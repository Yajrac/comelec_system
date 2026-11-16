"""SMS when an offline-saved registration is rejected as a duplicate (SMS sending mocked)."""
from datetime import date, timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from Applicants.models import Applicant, Barangay, DuplicateRegistrationNotice


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
@patch('core.views.send_sms', return_value=True)
class DuplicateRegistrationSmsTests(TestCase):
    def setUp(self):
        self.brgy = Barangay.objects.create(name='Agol')
        self.existing = Applicant.objects.create(
            lastname='Diaz', firstname='Maria', middlename='Palacio', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='X', phone='09171234567', brgy=self.brgy, status='PENDING')

    def sync(self, reference='WEB-OFFLINE-000000000001', phone='09171234567', offline=True):
        data = {'client_reference': reference, 'lastname': 'Diaz', 'firstname': 'Maria', 'middlename': 'Palacio',
                'birthdate': '2000-01-02', 'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'X',
                'brgy': self.brgy.pk, 'phone': phone, 'email': '', 'pwd_status': 'NO',
                'citizenship_status': 'BY_BIRTH', 'father': '', 'mother': '',
                'valid_id_document': SimpleUploadedFile('id.pdf', b'%PDF-1.7 test', content_type='application/pdf')}
        if offline:
            data['submitted_offline'] = '1'
        return self.client.post('/api/new-registration/', data)

    def test_same_phone_gets_status_and_reference(self, send):
        response = self.sync()
        self.assertEqual(response.status_code, 400)
        number, message = send.call_args.args
        self.assertEqual(number, '09171234567')
        self.assertIn('pending review', message)
        self.assertIn(self.existing.registration_reference, message)

    def test_approved_and_disapproved_messages(self, send):
        self.existing.status = 'APPROVED'
        self.existing.save()
        self.sync('WEB-OFFLINE-000000000002')
        self.assertIn('already registered', send.call_args.args[1])
        self.existing.status = 'DISAPPROVED'
        self.existing.save()
        DuplicateRegistrationNotice.objects.update(created_at=timezone.now() - timedelta(days=2))
        self.sync('WEB-OFFLINE-000000000003')
        self.assertIn('already exists', send.call_args.args[1])
        self.assertNotIn(self.existing.registration_reference, send.call_args.args[1])

    def test_different_phone_gets_only_already_exists(self, send):
        self.sync(phone='09998887777')
        number, message = send.call_args.args
        self.assertEqual(number, '09998887777')
        self.assertIn('already exists', message)
        self.assertNotIn(self.existing.registration_reference, message)
        self.assertNotIn('pending', message)

    def test_one_sms_per_form_and_per_number_a_day(self, send):
        self.sync()
        self.sync()                                   # the same form synced again
        self.sync('WEB-OFFLINE-000000000009')         # another form, same number, same day
        self.assertEqual(send.call_count, 1)

    def test_no_sms_for_online_submit_or_other_errors(self, send):
        self.sync(offline=False)
        Applicant.objects.all().delete()
        response = self.sync('WEB-OFFLINE-000000000004', phone='123')  # invalid phone: not a duplicate
        self.assertEqual(response.status_code, 400)
        send.assert_not_called()
