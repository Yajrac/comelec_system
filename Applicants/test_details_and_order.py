"""Birthdate and sex compared with the document (New Registration), and newest application first."""
from datetime import date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from Applicants.document_check import _iso_date, details_from, evaluate
from Applicants.models import Applicant, ApplicantTransferRequest, Barangay
from Applicants.test_document_check import AI_ON, pdf, reading

EXPECTED = {"last_name": "Diaz", "first_name": "Maria Althea", "middle_name": "Palacio"}


def read(birth='2000-01-02', sex='FEMALE'):
    return dict(reading(), birth_date=birth, sex=sex)


class DetailRuleTests(SimpleTestCase):
    def test_birthdate_and_sex(self):
        typed = {"birthdate": "2000-01-02", "sex": "FEMALE"}
        self.assertEqual(evaluate(read(), EXPECTED, '', typed)[0], 'passed')
        self.assertEqual(evaluate(read(birth='2000-02-01'), EXPECTED, '', typed)[0], 'birthdate_mismatch')
        self.assertEqual(evaluate(read(sex='MALE'), EXPECTED, '', typed)[0], 'sex_mismatch')
        self.assertEqual(evaluate(read(birth='', sex=''), EXPECTED, '', typed)[0], 'passed')   # not on the document
        self.assertEqual(evaluate(read(birth='1990-01-01'), EXPECTED, '', None)[0], 'passed')  # service request
        self.assertEqual(evaluate(dict(read(sex='MALE'), last_name='SANTOS'), EXPECTED, '', typed)[0], 'mismatch')

    def test_typed_details(self):
        self.assertEqual(details_from({"birthdate": "2000-01-02", "sex": "Female"}, "NEW"),
                         {"birthdate": "2000-01-02", "sex": "FEMALE"})
        self.assertIsNone(details_from({"birthdate": "2000-01-02", "sex": "Female"}, "UPDATE"))
        self.assertEqual(_iso_date("2000-01-02T00:00"), "2000-01-02")
        self.assertEqual(_iso_date("January 2, 2000"), "")
        self.assertEqual(_iso_date("2000-02-30"), "")


@override_settings(**AI_ON)
class DetailFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brgy = Barangay.objects.create(name='Agol')

    def form(self, **extra):
        data = {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': self.brgy.pk,
                'phone': '09171234567', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_document': pdf(), 'application_type': 'NEW'}
        data.update(extra)
        return data

    @patch('Applicants.document_check.ask_gemini', return_value=read(birth='1999-12-31'))
    def test_endpoint_reports_the_wrong_birthdate_without_revealing_it(self, ask):
        body = self.client.post('/document-check/', self.form()).json()
        self.assertEqual(body['status'], 'birthdate_mismatch')
        self.assertIn('birthdate you entered', body['message'])
        self.assertNotIn('1999', str(body))
        self.assertEqual(self.client.post('/document-check/', self.form(birthdate='1999-12-31')).json()['status'], 'passed')
        self.assertEqual(ask.call_count, 1)  # the document is read once; the comparison is redone

    @patch('Applicants.document_check.ask_gemini', return_value=read(sex='MALE'))
    def test_wrong_sex_blocks_the_submission(self, ask):
        response = self.client.post('/api/new-registration/', self.form())
        self.assertEqual(response.status_code, 400)
        self.assertIn('sex you selected', response.json()['error'])
        self.assertFalse(Applicant.objects.exists())

    @patch('Applicants.document_check.ask_gemini', return_value=read())
    def test_matching_details_pass_and_the_officer_sees_them(self, ask):
        self.assertEqual(self.client.post('/api/new-registration/', self.form()).status_code, 201)
        applicant = Applicant.objects.get()
        self.client.force_login(get_user_model().objects.create_superuser(username='detailofficer', password='x'))
        page = self.client.get(f'/comelec/admin-applications/new/{applicant.pk}/')
        self.assertContains(page, 'Birthdate on document')
        self.assertContains(page, 'Sex on document')


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class NewestFirstTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='orderadmin', password='x'))
        self.brgy = Barangay.objects.create(name='Agol')

    def make(self, name):
        return Applicant.objects.create(lastname=name, firstname='Ana', age=26, sex='Female', birthdate=date(2000, 1, 2),
                                        birthplace='X', phone='09171234567', brgy=self.brgy)

    def test_new_registrations_get_their_time(self):
        before = timezone.now()
        self.assertGreaterEqual(self.make('Timed').submitted_at, before)

    def test_newest_is_first_even_on_the_same_day(self):
        today = timezone.localtime().replace(hour=8, minute=0, second=0, microsecond=0)
        older, newer = self.make('Older'), self.make('Newer')
        Applicant.objects.filter(pk=older.pk).update(submitted_at=today)
        Applicant.objects.filter(pk=newer.pk).update(submitted_at=today + timedelta(hours=12))  # 8:00 PM
        transfer = ApplicantTransferRequest.objects.create(applicant=older, current_brgy=self.brgy, new_brgy=self.brgy,
                                                           status='PENDING')
        ApplicantTransferRequest.objects.filter(pk=transfer.pk).update(requested_at=today + timedelta(hours=10))
        legacy = self.make('Legacy')
        Applicant.objects.filter(pk=legacy.pk).update(submitted_at=None, date_joined=(today - timedelta(days=1)).date())
        response = self.client.get('/comelec/admin-applications/')
        order = [(item['type'], item['applicant_name'].split(',')[0]) for item in response.context['page_obj']]
        self.assertEqual(order, [('NEW', 'Newer'), ('TRANSFER', 'Older'), ('NEW', 'Older'), ('NEW', 'Legacy')])
        self.assertContains(response, '&mdash;')  # an older registration has no recorded time
