"""The uploaded document must be the type the applicant chose (detected code compared, never text)."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from Applicants.document_check import PROMPT, evaluate
from Applicants.models import Applicant, Barangay, DocumentCheck
from Applicants.test_document_check import AI_ON, pdf, reading

EXPECTED = {"last_name": "Diaz", "first_name": "Maria Althea", "middle_name": "Palacio"}


def coded(code, **extra):
    return dict(reading(**extra), document_code=code)


class TypeRuleTests(SimpleTestCase):
    def test_prompt_lists_every_code(self):
        for code in ('PHILSYS', 'SSS_GSIS_UMID', 'PSA_BIRTH_CERTIFICATE', 'OTHER_GOVERNMENT'):
            self.assertIn(code, PROMPT)

    def test_rules(self):
        self.assertEqual(evaluate(coded('POSTAL'), EXPECTED, 'POSTAL')[0], 'passed')
        status, reason = evaluate(coded('DRIVERS_LICENSE'), EXPECTED, 'POSTAL')
        self.assertEqual(status, 'type_mismatch')
        self.assertIn("LTO Driver's License / Student Permit, not Postal ID", reason)
        self.assertEqual(evaluate(coded(''), EXPECTED, 'POSTAL')[0], 'passed')          # unsure: officer reviews
        self.assertEqual(evaluate(reading(), EXPECTED, 'POSTAL')[0], 'passed')          # old reading, no code
        self.assertEqual(evaluate(coded('POSTAL'), EXPECTED, '')[0], 'passed')          # no type chosen (old app)
        self.assertEqual(evaluate(coded('POSTAL'), EXPECTED, 'OTHER_GOVERNMENT')[0], 'type_mismatch')
        self.assertEqual(evaluate(coded('OTHER_GOVERNMENT'), EXPECTED, 'OTHER_GOVERNMENT')[0], 'passed')
        self.assertIn('another government ID', evaluate(coded('OTHER_GOVERNMENT'), EXPECTED, 'POSTAL')[1])

    def test_invalid_document_wins_over_type(self):
        self.assertEqual(evaluate(coded('POSTAL', valid=False), EXPECTED, 'PASSPORT')[0], 'invalid')

    def test_type_is_reported_before_the_name(self):
        self.assertEqual(evaluate(coded('POSTAL', last='SANTOS'), EXPECTED, 'PASSPORT')[0], 'type_mismatch')


@override_settings(**AI_ON)
class TypeFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brgy = Barangay.objects.create(name='Agol')

    def check(self, file, id_type):
        return self.client.post('/document-check/', {
            'valid_id_document': file, 'application_type': 'NEW', 'valid_id_type': id_type,
            'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio'}).json()

    def registration(self, file, id_type, **extra):
        data = {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': self.brgy.pk,
                'phone': '09171234567', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_document': file, 'valid_id_type': id_type}
        data.update(extra)
        return data

    @patch('Applicants.document_check.ask_gemini')
    def test_endpoint_reports_the_wrong_type_and_rechecks_without_reading_again(self, ask):
        ask.return_value = coded('DRIVERS_LICENSE')
        body = self.check(pdf(), 'POSTAL')
        self.assertEqual(body['status'], 'type_mismatch')
        self.assertIn('not Postal ID', body['message'])
        self.assertEqual(body['document_type'], "LTO Driver's License / Student Permit")
        self.assertEqual(self.check(pdf(), 'DRIVERS_LICENSE')['status'], 'passed')     # type changed
        self.assertEqual(ask.call_count, 1)

    @patch('Applicants.document_check.ask_gemini')
    def test_wrong_type_blocks_api_and_web_submit(self, ask):
        ask.return_value = coded('DRIVERS_LICENSE')
        response = self.client.post('/api/new-registration/', self.registration(pdf(), 'POSTAL'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('not Postal ID', response.json()['error'])
        self.assertFalse(Applicant.objects.exists())
        response = self.client.post('/api/new-registration/', self.registration(pdf(), 'DRIVERS_LICENSE'))
        self.assertEqual(response.status_code, 201, response.content)

    @patch('Applicants.document_check.ask_gemini')
    def test_walk_in_officer_can_override_a_wrong_type(self, ask):
        ask.return_value = coded('DRIVERS_LICENSE')
        self.client.force_login(get_user_model().objects.create_superuser(username='typeofficer', password='x'))
        from Applicants.test_id_type_selfie import selfie
        with override_settings(REQUIRE_ID_TYPE_AND_SELFIE=False):
            self.client.post('/comelec/walk-in/new/', self.registration(pdf(), 'POSTAL', officer_verified='1',
                                                                       photo=selfie()))
        applicant = Applicant.objects.get()
        check = DocumentCheck.objects.get(application_type='NEW', record_id=applicant.pk)
        self.assertEqual(check.status, 'override')
        response = self.client.get(f'/comelec/admin-applications/new/{applicant.pk}/')
        self.assertContains(response, 'Postal ID')
        self.assertContains(response, "LTO Driver&#x27;s License / Student Permit")
