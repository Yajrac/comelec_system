"""Certain vs possible duplicates, tidy names, admin comparison and filter."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from Applicants.duplicates import CERTAIN, POSSIBLE, compact, match_level
from Applicants.models import Applicant, Barangay


class Person:
    def __init__(self, last, first, middle=''):
        self.lastname, self.firstname, self.middlename = last, first, middle


class MatchRuleTests(SimpleTestCase):
    def test_certain_matches_ignore_case_spacing_accents_and_ma(self):
        old = Person('Dela Cruz', 'Maria Elena', 'Peña')
        for last, first, middle in [('DELACRUZ', 'maria elena', 'PENA'), ('dela  cruz', 'Ma. Elena', 'Pena'),
                                    ('Dela-Cruz', 'MARIA ELENA', 'peña')]:
            self.assertEqual(match_level(old, last, first, middle), CERTAIN, (last, first, middle))
        self.assertEqual(match_level(Person('Diaz', 'Juan'), 'Diaz', 'Juan Jr.', ''), CERTAIN)

    def test_possible_matches(self):
        old = Person('Diaz', 'Maria Althea', 'Palacio')
        self.assertEqual(match_level(old, 'Diaz', 'Maria Althea', ''), POSSIBLE)    # middle name blank
        self.assertEqual(match_level(old, 'Diaz', 'Maria Althea', 'P.'), POSSIBLE)  # middle initial
        self.assertEqual(match_level(old, 'Diaz', 'Maria', 'Palacio'), POSSIBLE)    # second name omitted

    def test_not_matches(self):
        old = Person('Diaz', 'Maria', 'Palacio')
        self.assertIsNone(match_level(old, 'Dias', 'Maria', 'Palacio'))
        self.assertIsNone(match_level(old, 'Diaz', 'Mariel', 'Palacio'))
        self.assertIsNone(match_level(old, 'Diaz', 'Maria', 'Santos'))
        self.assertEqual(compact('  Dela   Cruz '), 'DELACRUZ')


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
@patch('core.views.send_sms', return_value=True)
class DuplicateLevelFlowTests(TestCase):
    def setUp(self):
        self.brgy = Barangay.objects.create(name='Agol')
        self.existing = Applicant.objects.create(
            lastname='Dela Cruz', firstname='Maria', middlename='Peña', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='Pio Duran', phone='09171234567', brgy=self.brgy, status='APPROVED')

    def form(self, **extra):
        data = {'lastname': 'DelaCruz', 'firstname': 'Maria', 'middlename': 'Pena', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': self.brgy.pk,
                'phone': '09170000000', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '',
                'valid_id_document': SimpleUploadedFile('id.pdf', b'%PDF-1.7 test', content_type='application/pdf')}
        data.update(extra)
        return data

    def test_certain_online_is_refused_even_with_different_spelling(self, send):
        response = self.client.post('/api/new-registration/', self.form(client_reference='WEB-ONLINE-0000000001'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'DUPLICATE_REGISTRATION')
        verify = self.client.post('/verify-new-registration/', {
            'lastname': 'DELA CRUZ', 'firstname': 'maria', 'middlename': 'PENA', 'birthdate': '2000-01-02'})
        self.assertContains(verify, 'Registration already exists')

    def test_possible_online_is_saved_pending_without_sms(self, send):
        verify = self.client.post('/verify-new-registration/', {
            'lastname': 'Dela Cruz', 'firstname': 'Maria', 'middlename': '', 'birthdate': '2000-01-02'})
        self.assertEqual(verify.status_code, 302)  # possible match continues to the form
        response = self.client.post('/api/new-registration/', self.form(middlename='', client_reference='WEB-ONLINE-0000000002'))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(response.json()['possible_duplicate'])
        new = Applicant.objects.get(pk=response.json()['applicant_id'])
        self.assertEqual(new.possible_duplicate_of, self.existing)
        send.assert_not_called()
        self.assertContains(self.client.get(f'/registration-success/{new.pk}/'), 'possible duplicate')

    def test_possible_on_the_web_form_and_offline_certain_sends_sms(self, send):
        response = self.client.post('/new-registration/', self.form(middlename='P.'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Applicant.objects.filter(possible_duplicate_of=self.existing).count(), 1)
        offline = self.client.post('/api/new-registration/', self.form(
            phone='09175550000', client_reference='WEB-OFFLINE-0000000003', submitted_offline='1'))
        self.assertEqual(offline.status_code, 201)
        send.assert_called_once()

    def test_names_are_tidied_when_saved(self, send):
        applicant = Applicant.objects.create(lastname='  Santos ', firstname='Ana   Marie', middlename=' Reyes',
                                             age=30, sex='Female', birthdate=date(1996, 1, 2), birthplace=' Legazpi  City ',
                                             phone='09170000001')
        applicant.refresh_from_db()
        self.assertEqual((applicant.lastname, applicant.firstname, applicant.middlename, applicant.birthplace),
                         ('Santos', 'Ana Marie', 'Reyes', 'Legazpi City'))

    def test_admin_comparison_and_filter(self, send):
        new = Applicant.objects.get(pk=self.client.post('/api/new-registration/', self.form(
            middlename='', client_reference='WEB-ONLINE-0000000004')).json()['applicant_id'])
        self.client.force_login(get_user_model().objects.create_superuser(username='compareadmin', password='x'))
        detail = self.client.get(f'/comelec/admin-applications/new/{new.pk}/')
        self.assertContains(detail, 'Compare both records')
        self.assertContains(detail, 'Existing record')
        self.assertContains(detail, 'Birthplace')
        listing = self.client.get('/comelec/admin-applications/', {'status': 'POSSIBLE_DUPLICATE'})
        self.assertEqual([row['id'] for row in listing.context['page_obj']], [new.pk])
