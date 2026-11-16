"""Offline-synced duplicates: kept as PENDING possible duplicates, applicant told by SMS (SMS mocked)."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from Applicants.models import Applicant, Barangay
from Applicants.status import lookup


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
@patch('core.views.send_sms', return_value=True)
class OfflineDuplicateTests(TestCase):
    def setUp(self):
        self.brgy = Barangay.objects.create(name='Agol')
        self.existing = Applicant.objects.create(
            lastname='Diaz', firstname='Maria', middlename='Palacio', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='X', phone='09171234567', email='maria@example.com',
            brgy=self.brgy, status='APPROVED')

    def sync(self, reference='WEB-OFFLINE-000000000001', phone='09171234567', email='', offline=True):
        data = {'client_reference': reference, 'lastname': 'Diaz', 'firstname': 'Maria', 'middlename': 'Palacio',
                'birthdate': '2000-01-02', 'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'X',
                'brgy': self.brgy.pk, 'phone': phone, 'email': email, 'pwd_status': 'NO',
                'citizenship_status': 'BY_BIRTH', 'father': '', 'mother': '',
                'valid_id_document': SimpleUploadedFile('id.pdf', b'%PDF-1.7 test', content_type='application/pdf')}
        if offline:
            data['submitted_offline'] = '1'
        return self.client.post('/api/new-registration/', data)

    def test_offline_duplicate_is_saved_as_pending_and_texted(self, send):
        response = self.sync()
        self.assertEqual(response.status_code, 201, response.content)
        duplicate = Applicant.objects.get(pk=response.json()['applicant_id'])
        self.assertEqual((duplicate.status, duplicate.possible_duplicate_of), ('PENDING', self.existing))
        number, message = send.call_args.args
        self.assertEqual(number, '09171234567')
        self.assertIn('pending due to a possible duplicate', message)
        self.assertIn(duplicate.registration_reference, message)
        self.assertNotIn(self.existing.registration_reference, message)  # nothing about the other record

    def test_online_duplicate_is_still_refused_without_sms(self, send):
        response = self.sync(offline=False)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Applicant.objects.count(), 1)
        send.assert_not_called()

    def test_same_email_stays_on_the_existing_record(self, send):
        response = self.sync(email='maria@example.com')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(Applicant.objects.get(pk=response.json()['applicant_id']).email)

    def test_one_sms_per_form_and_per_number_a_day(self, send):
        self.sync()
        self.sync()                                    # same form re-synced: replayed, not saved twice
        self.sync('WEB-OFFLINE-000000000009')          # another form, same number, same day
        self.assertEqual(Applicant.objects.filter(possible_duplicate_of=self.existing).count(), 2)
        self.assertEqual(send.call_count, 1)

    def test_officer_and_status_page_see_the_possible_duplicate(self, send):
        duplicate = Applicant.objects.get(pk=self.sync().json()['applicant_id'])
        self.client.force_login(get_user_model().objects.create_superuser(username='dupadmin', password='x'))
        self.assertContains(self.client.get('/comelec/admin-applications/'), 'Possible duplicate')
        detail = self.client.get(f'/comelec/admin-applications/new/{duplicate.pk}/')
        self.assertContains(detail, 'Possible duplicate.')
        self.assertContains(detail, f'/comelec/admin-applications/new/{self.existing.pk}/')
        result = lookup(duplicate.registration_reference)
        self.assertEqual(result['rows'][0]['status'], 'Pending - possible duplicate')

    def test_disapproving_a_possible_duplicate_explains_why(self, send):
        duplicate = Applicant.objects.get(pk=self.sync().json()['applicant_id'])
        self.client.force_login(get_user_model().objects.create_superuser(username='dupdecide', password='x'))
        self.client.post(f'/comelec/admin-applications/new/{duplicate.pk}/disapprove/')
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.status, 'DISAPPROVED')
        message = send.call_args.args[1]
        self.assertIn('DISAPPROVED because you already have a registration', message)
        self.assertLessEqual(len(message), 306)
