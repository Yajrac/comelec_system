"""AI document check: name rules, blocking, caching, fallbacks and walk-in override (AI mocked)."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from Applicants.document_check import DocumentAIUnavailable, names_match
from Applicants.models import Applicant, ApplicantTransferRequest, Barangay, DocumentCheck

AI_ON = dict(DOCUMENT_AI_PROVIDER="gemini", GEMINI_API_KEY="test-key", DOCUMENT_AI_MAX_PER_MINUTE=0,
             PAGE_RATE_LIMIT_REQUESTS=0,
             STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                       'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})


def reading(last='DIAZ', first='MARIA ALTHEA', middle='PALACIO', valid=True, readable=True, reason=''):
    return {"is_valid_document": valid, "is_readable": readable, "document_type": "PhilSys National ID",
            "last_name": last, "first_name": first, "middle_name": middle, "reason": reason}


def pdf(content=b'one'):
    return SimpleUploadedFile('id.pdf', b'%PDF-1.7 ' + content, content_type='application/pdf')


class NameRuleTests(SimpleTestCase):
    def expect(self, last, first, middle=''):
        return {"last_name": last, "first_name": first, "middle_name": middle}

    def test_matching_rules(self):
        form = self.expect('Diaz', 'Maria Althea', 'Palacio')
        self.assertTrue(names_match(form, reading()))
        self.assertTrue(names_match(form, reading(middle='P.')))             # middle initial
        self.assertTrue(names_match(form, reading(middle='')))               # no middle on ID
        self.assertTrue(names_match(form, reading(first='MARIA')))           # second name omitted
        self.assertTrue(names_match(self.expect('Peña', 'Juan'), reading(last='PENA', first='JUAN', middle='')))
        self.assertTrue(names_match(self.expect('Cruz', 'Juan Jr.'), reading(last='CRUZ', first='JUAN', middle='')))

    def test_mismatches(self):
        form = self.expect('Diaz', 'Maria Althea', 'Palacio')
        self.assertFalse(names_match(form, reading(last='DIAS')))
        self.assertFalse(names_match(form, reading(first='MARIANNE')))
        self.assertFalse(names_match(form, reading(middle='SANTOS')))
        self.assertFalse(names_match(form, reading(last='', first='')))


@override_settings(**AI_ON)
class DocumentCheckFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brgy = Barangay.objects.create(name='Agol')

    def post_check(self, file, **names):
        data = {'valid_id_document': file, 'application_type': 'NEW'}
        data.update(names or {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio'})
        return self.client.post('/document-check/', data)

    def registration(self, file, **extra):
        data = {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': self.brgy.pk,
                'phone': '09171234567', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_document': file}
        data.update(extra)
        return self.client.post('/api/new-registration/', data)

    @patch('Applicants.document_check.ask_gemini')
    def test_endpoint_reports_the_three_results(self, ask):
        ask.return_value = reading()
        self.assertEqual(self.post_check(pdf(b'a')).json()['status'], 'passed')
        ask.return_value = reading(valid=False, reason='This is a selfie.')
        body = self.post_check(pdf(b'b')).json()
        self.assertEqual(body['status'], 'invalid')
        self.assertIn('not valid', body['message'])
        ask.return_value = reading(last='SANTOS')
        body = self.post_check(pdf(b'c')).json()
        self.assertEqual(body['status'], 'mismatch')
        self.assertNotIn('SANTOS', str(body))  # the name on someone else's document is not revealed
        ask.return_value = reading(readable=False, reason='Too blurry.')
        self.assertEqual(self.post_check(pdf(b'd')).json()['status'], 'invalid')

    @patch('Applicants.document_check.ask_gemini')
    def test_upload_before_typing_the_name_checks_validity_then_name_on_submit(self, ask):
        ask.return_value = reading(last='SANTOS')
        body = self.client.post('/document-check/', {'valid_id_document': pdf(), 'application_type': 'NEW'}).json()
        self.assertEqual(body['status'], 'valid')
        self.assertNotIn('expected_name', body)
        self.assertEqual(self.post_check(pdf()).json()['status'], 'mismatch')  # name typed now, same file
        self.assertEqual(self.registration(pdf()).status_code, 400)
        self.assertEqual(ask.call_count, 1)  # the document was read by the AI only once

    @patch('Applicants.document_check.ask_gemini')
    def test_same_file_is_read_once_and_submission_is_linked(self, ask):
        ask.return_value = reading()
        self.post_check(pdf())
        response = self.registration(pdf())
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(ask.call_count, 1)
        applicant = Applicant.objects.get()
        check = DocumentCheck.objects.get(application_type='NEW', record_id=applicant.pk)
        self.assertEqual(check.status, 'passed')

    @patch('Applicants.document_check.ask_gemini')
    def test_invalid_or_mismatched_document_blocks_submission(self, ask):
        ask.return_value = reading(last='SANTOS')
        response = self.registration(pdf())
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not match the name you entered', response.json()['error'])
        self.assertFalse(Applicant.objects.exists())

    @patch('Applicants.document_check.ask_gemini', side_effect=DocumentAIUnavailable('error'))
    def test_ai_down_lets_the_application_through_flagged(self, ask):
        self.assertEqual(self.post_check(pdf()).json()['status'], 'unavailable')
        self.assertEqual(self.registration(pdf()).status_code, 201)
        applicant = Applicant.objects.get()
        self.assertEqual(DocumentCheck.objects.get(record_id=applicant.pk).status, 'unavailable')

    @patch('Applicants.document_check.ask_gemini')
    def test_service_request_compares_with_the_registered_name(self, ask):
        applicant = Applicant.objects.create(lastname='Diaz', firstname='Maria Althea', middlename='Palacio', age=26,
                                             sex='Female', birthdate=date(2000, 1, 2), birthplace='X',
                                             phone='09171234567', brgy=self.brgy, status='APPROVED')
        ask.return_value = reading(last='SANTOS')
        body = self.client.post('/document-check/', {'valid_id_document': pdf(), 'applicant_id': applicant.pk}).json()
        self.assertEqual(body['status'], 'mismatch')
        self.assertNotIn('expected_name', body)  # the stored name is never echoed back

    @patch('Applicants.document_check.ask_gemini')
    def test_walk_in_officer_can_confirm_a_failed_document(self, ask):
        ask.return_value = reading(valid=False, reason='Unclear photo.')
        admin = get_user_model().objects.create_superuser(username='walkinai', password='test-password')
        self.client.force_login(admin)
        applicant = Applicant.objects.create(lastname='Diaz', firstname='Maria Althea', middlename='Palacio', age=26,
                                             sex='Female', birthdate=date(2000, 1, 2), birthplace='X',
                                             phone='09171234567', brgy=self.brgy, status='APPROVED')
        new_brgy = Barangay.objects.create(name='Binodegahan')
        data = {'action': 'submit_transfer', 'applicant_id': applicant.pk, 'new_brgy': new_brgy.pk,
                'new_municipality': 'Pio Duran', 'new_province': 'Albay', 'reason': 'Moved to a new barangay.',
                'valid_id_document': pdf()}
        self.client.post('/comelec/walk-in/transfer/', data)
        self.assertFalse(ApplicantTransferRequest.objects.exists())
        data['valid_id_document'] = pdf()
        data['officer_verified'] = '1'
        self.client.post('/comelec/walk-in/transfer/', data)
        transfer = ApplicantTransferRequest.objects.get()
        check = DocumentCheck.objects.get(application_type='TRANSFER', record_id=transfer.pk)
        self.assertEqual((check.status, check.officer), ('override', admin))

    @patch('Applicants.document_check.ask_gemini')
    def test_public_form_cannot_use_the_officer_override(self, ask):
        ask.return_value = reading(valid=False)
        response = self.registration(pdf(), officer_verified='1')
        self.assertEqual(response.status_code, 400)

    @override_settings(DOCUMENT_AI_MAX_PER_MINUTE=1)
    def test_shared_limit_turns_extra_checks_into_not_checked(self):
        with patch('Applicants.document_check._take_ai_slot', side_effect=[True, False]), \
                patch('google.genai.Client') as client:
            client.return_value.models.generate_content.return_value.text = (
                '{"is_valid_document": true, "is_readable": true, "document_type": "ID", '
                '"last_name": "DIAZ", "first_name": "MARIA ALTHEA", "middle_name": ""}')
            self.assertEqual(self.post_check(pdf(b'1')).json()['status'], 'passed')
            self.assertEqual(self.post_check(pdf(b'2')).json()['status'], 'unavailable')


@override_settings(**AI_ON)
class DocumentCheckPageTests(TestCase):
    def test_forms_are_marked_only_when_the_feature_is_on(self):
        page = self.client.get('/new-registration/')
        self.assertContains(page, 'data-document-check="NEW"')
        self.assertContains(page, 'js/document-check.js')
        self.assertContains(page, 'data-document-ai="1"')
        self.assertNotContains(page, 'data-walk-in="1"')
        with self.settings(DOCUMENT_AI_PROVIDER=''):
            page = self.client.get('/new-registration/')
            self.assertNotContains(page, 'data-document-check=')
            self.assertEqual(self.client.post('/document-check/', {}).json()['status'], 'disabled')

    def test_walk_in_form_offers_the_officer_override(self):
        admin = get_user_model().objects.create_superuser(username='walkinpage', password='test-password')
        self.client.force_login(admin)
        self.assertContains(self.client.get('/comelec/walk-in/new/'), 'data-walk-in="1"')

    @patch('Applicants.document_check.ask_gemini')
    def test_admin_detail_shows_the_check(self, ask):
        ask.return_value = reading()
        admin = get_user_model().objects.create_superuser(username='badgeadmin', password='test-password')
        brgy = Barangay.objects.create(name='Agol')
        data = {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': brgy.pk,
                'phone': '09171234567', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_document': pdf()}
        self.assertEqual(self.client.post('/api/new-registration/', data).status_code, 201)
        self.client.force_login(admin)
        applicant = Applicant.objects.get()
        page = self.client.get(f'/comelec/admin-applications/new/{applicant.pk}/')
        self.assertContains(page, 'Valid, name matches')
        self.assertContains(page, 'PhilSys National ID')
