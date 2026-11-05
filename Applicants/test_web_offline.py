from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from Applicants.models import Applicant, Barangay, MobileSubmissionReceipt


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class WebOfflineTests(TestCase):
    def setUp(self):
        self.barangay = Barangay.objects.create(name='Offline test barangay')

    def payload(self, reference):
        return {
            'client_reference': reference,
            'lastname': 'Offline', 'firstname': 'Applicant', 'middlename': '',
            'birthdate': '2000-01-02', 'age': '26', 'sex': 'Male', 'civil_status': 'Single',
            'birthplace': 'Pio Duran', 'brgy': self.barangay.pk,
            'phone': '09171234567', 'email': '', 'pwd_status': 'NO',
            'citizenship_status': 'BY_BIRTH', 'father': '', 'mother': '',
            'valid_id_document': SimpleUploadedFile('support.pdf', b'%PDF-1.7 test document'),
        }

    def test_replay_uses_existing_confirmation_even_if_original_data_changes(self):
        reference = 'WEB-OFFLINE-000000000001'
        first = self.client.post('/api/new-registration/', self.payload(reference))
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()['success_url'], f"/registration-success/{first.json()['applicant_id']}/")
        replay = self.client.post('/api/new-registration/', {'client_reference': reference})
        self.assertEqual(replay.status_code, 201, replay.content)
        self.assertEqual(first.json(), replay.json())
        self.assertEqual(Applicant.objects.count(), 1)
        self.assertEqual(MobileSubmissionReceipt.objects.count(), 1)

    def test_different_submission_id_does_not_bypass_identity_check(self):
        first = self.client.post('/api/new-registration/', self.payload('WEB-OFFLINE-000000000002'))
        self.assertEqual(first.status_code, 201, first.content)
        duplicate = self.client.post('/api/new-registration/', self.payload('WEB-OFFLINE-000000000003'))
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Applicant.objects.count(), 1)
        self.assertEqual(MobileSubmissionReceipt.objects.count(), 1)

    def test_sync_confirmation_opens_the_normal_registration_success_page(self):
        saved = self.client.post('/api/new-registration/', self.payload('WEB-OFFLINE-000000000004'))
        self.assertEqual(saved.status_code, 201, saved.content)
        confirmation = self.client.get(saved.json()['success_url'])
        self.assertEqual(confirmation.status_code, 200)
        self.assertTemplateUsed(confirmation, 'components/registration_success.html')
        self.assertContains(confirmation, saved.json()['registration_reference'])

    def test_offline_shell_never_restores_posted_or_session_data(self):
        user = get_user_model().objects.create_superuser(username='offlineadmin', password='test-password')
        self.client.force_login(user)
        response = self.client.get('/offline/shell/registration/?firstname=PrivateName')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.barangay.name)
        self.assertNotContains(response, 'PrivateName')
        self.assertNotContains(response, 'offlineadmin')
        self.assertNotContains(response, 'name="csrfmiddlewaretoken"')
        self.assertIn('no-store', response['Cache-Control'])

    def test_worker_and_ping_are_same_origin_and_uncached(self):
        response = self.client.get('/web-offline-sw.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertContains(response, '/offline/shell/registration/')
        self.assertNotContains(response, '{{')
        ping = self.client.get('/offline/connection/')
        self.assertEqual(ping.json(), {'online': True})
        self.assertIn('no-store', ping['Cache-Control'])

    def test_saved_panel_is_on_offline_page_and_linked_in_header(self):
        response = self.client.get('/offline/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'applicant/offline.html')
        self.assertContains(response, 'id="publicMenuToggle"')
        self.assertContains(response, 'href="/offline/"')
        shell = self.client.get('/offline/shell/saved/')
        self.assertEqual(shell.status_code, 200)
        self.assertContains(shell, 'Saved applications')

    def test_walk_in_page_does_not_enable_public_offline_queue(self):
        user = get_user_model().objects.create_superuser(username='walkinoffline', password='test-password')
        self.client.force_login(user)
        response = self.client.get('/comelec/walk-in/new/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="webOfflinePanel"')
