"""Duplicate registration modals: applicants see no details; officers see the existing record."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from Applicants.models import Applicant, Barangay


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DuplicateModalTests(TestCase):
    def setUp(self):
        self.brgy = Barangay.objects.create(name='Binodegahan')
        self.existing = Applicant.objects.create(
            lastname='Diaz', firstname='Maria', middlename='Palacio', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='Legazpi', phone='09171234567', brgy=self.brgy, status='APPROVED')

    def form(self, **extra):
        data = {'lastname': 'Diaz', 'firstname': 'Maria', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'X', 'brgy': self.brgy.pk,
                'phone': '09170000000', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '',
                'valid_id_document': SimpleUploadedFile('id.pdf', b'%PDF-1.7 test', content_type='application/pdf')}
        data.update(extra)
        return data

    def assert_public_modal(self, response):
        html = response.content.decode()
        start = html.index('<dialog id="duplicateRegistrationDialog"')
        dialog = html[start:html.index('</dialog>', start)]
        for text in ('Registration already exists', 'Check my status', 'Choose another service'):
            self.assertIn(text, dialog)
        for private in ('Binodegahan', 'Legazpi', 'Approved', 'Palacio'):
            self.assertNotIn(private, dialog)
        self.assertNotIn('Existing Registration Found', html)

    def test_verify_step_shows_the_modal_without_record_details(self):
        response = self.client.post('/verify-new-registration/', {
            'lastname': 'Diaz', 'firstname': 'Maria', 'middlename': 'Palacio', 'birthdate': '2000-01-02'})
        self.assertEqual(response.status_code, 200)
        self.assert_public_modal(response)

    def test_online_form_submit_shows_the_modal(self):
        response = self.client.post('/new-registration/', self.form())
        self.assert_public_modal(response)
        self.assertEqual(Applicant.objects.count(), 1)

    def test_api_marks_online_duplicates_for_the_page_script(self):
        response = self.client.post('/api/new-registration/', self.form(client_reference='WEB-ONLINE-0000000001'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'DUPLICATE_REGISTRATION')

    @patch('core.views.send_sms', return_value=True)
    def test_offline_sync_reply_flags_the_pending_duplicate(self, send):
        response = self.client.post('/api/new-registration/', self.form(
            client_reference='WEB-OFFLINE-0000000001', submitted_offline='1'))
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['possible_duplicate'])

    def test_walk_in_officer_sees_the_existing_record(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='walkindup', password='x'))
        response = self.client.post('/comelec/walk-in/new/', self.form())
        self.assertContains(response, 'Registration already exists')
        self.assertContains(response, 'Open existing record')
        self.assertContains(response, f'/comelec/admin-applications/new/{self.existing.pk}/')
        self.assertContains(response, 'Diaz, Maria Palacio')
        self.assertNotContains(response, 'Choose another service')
