from datetime import date
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from Applicants.eligibility import age_eligibility
from Applicants.models import Applicant, Barangay

@override_settings(VOTER_ELECTION_DATE='2028-11-13', STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ElectionAgeTests(TestCase):
    def test_exact_birthday_boundaries_and_categories(self):
        self.assertTrue(age_eligibility(date(2013, 11, 13))['eligible'])
        self.assertFalse(age_eligibility(date(2013, 11, 14))['eligible'])
        self.assertEqual(age_eligibility(date(2013, 11, 13)), {'age': 15, 'eligible': True, 'sk': True, 'regular': False})
        self.assertEqual(age_eligibility(date(2010, 11, 13)), {'age': 18, 'eligible': True, 'sk': True, 'regular': True})
        self.assertTrue(age_eligibility(date(1998, 11, 13))['sk'])
        self.assertFalse(age_eligibility(date(1997, 11, 13))['sk'])
        self.assertTrue(age_eligibility(date(1997, 11, 13))['regular'])

    def test_configurable_date_accepts_fourteen_turning_fifteen(self):
        with self.settings(VOTER_ELECTION_DATE='2026-11-02'):
            self.assertTrue(age_eligibility(date(2011, 11, 2))['eligible'])
            self.assertFalse(age_eligibility(date(2011, 11, 3))['eligible'])

    @patch('Applicants.validation.timezone.localdate', return_value=date(2026, 11, 1))
    def test_registration_enforces_election_age_and_retains_current_age(self, _today):
        barangay = Barangay.objects.create(name='Caratagan')
        payload = {'firstname': 'Juan', 'lastname': 'Cruz', 'middlename': '', 'email': '',
            'birthdate': '2013-11-14', 'age': '99', 'sex': 'Male', 'civil_status': 'Single',
            'brgy': barangay.pk, 'birthplace': 'Pio Duran', 'municipality': 'Pio Duran', 'province': 'Albay',
            'phone': '09171234567', 'father': 'Pedro Cruz', 'mother': 'Maria Cruz',
            'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH'}
        response = self.client.post(reverse('new-registration'), payload)
        self.assertContains(response, 'at least 15 years old on election day')
        self.assertFalse(Applicant.objects.exists())
        payload['birthdate'] = '2030-01-01'
        self.client.post(reverse('new-registration'), payload)
        self.assertFalse(Applicant.objects.exists())
        payload['birthdate'] = '2013-11-13'
        payload['valid_id_document'] = SimpleUploadedFile('id.pdf', b'%PDF-1.7 sample')
        response = self.client.post(reverse('new-registration'), payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Applicant.objects.get().age, 12)
