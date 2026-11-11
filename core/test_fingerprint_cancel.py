"""Officers can cancel a waiting fingerprint capture without losing the saved image."""
import base64
import io
import json
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from Applicants.models import Applicant, ApplicantBiometric, FingerprintCaptureRequest


def bmp_upload():
    output = io.BytesIO()
    Image.new('L', (256, 288), 128).save(output, format='BMP')
    return SimpleUploadedFile('finger.bmp', output.getvalue(), content_type='image/bmp')


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0, STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class FingerprintCancelTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username='fpadmin', password='test-password')
        self.client.force_login(self.admin)
        self.applicant = Applicant.objects.create(
            lastname='Scan', firstname='Test', middlename='', age=26, sex='Male', birthdate=date(2000, 1, 2),
            birthplace='Pio Duran', phone='09171234567', status='APPROVED', verification_status='BIOMETRICS_PENDING')
        self.biometric = ApplicantBiometric.objects.create(applicant=self.applicant)
        self.biometric.left_finger.save('kept.png', ContentFile(b'old'), save=True)

    def start(self, finger='left'):
        response = self.client.post(reverse('start-fingerprint-capture', args=[self.applicant.pk]), {'finger': finger})
        return response.json()['request_id']

    def upload_image(self, finger='left'):
        return self.client.post(reverse('save-fingerprint', args=[self.applicant.pk]),
                                {'finger': finger, 'fingerprint': bmp_upload()})

    def upload_template(self, finger='left'):
        return self.client.post(reverse('fingerprint-device-upload', args=[self.applicant.pk]),
                                json.dumps({'finger': finger, 'template': base64.b64encode(b'tpl').decode()}),
                                content_type='application/json')

    def test_cancel_before_device_accepts_is_never_picked_up(self):
        request_id = self.start()
        response = self.client.post(reverse('cancel-fingerprint-capture', args=[request_id]))
        self.assertEqual(response.json()['status'], 'cancelled')
        self.assertEqual(self.client.get(reverse('fingerprint-device-next')).json(), {'command': None})
        status = self.client.get(reverse('fingerprint-capture-status', args=[request_id])).json()
        self.assertEqual(status['status'], 'cancelled')

    def test_upload_after_cancel_is_rejected_and_saved_image_kept(self):
        request_id = self.start()
        self.assertEqual(self.client.get(reverse('fingerprint-device-next')).json()['request_id'], request_id)
        self.client.post(reverse('cancel-fingerprint-capture', args=[request_id]))
        self.assertEqual(self.upload_image().status_code, 409)
        self.assertEqual(self.upload_template().status_code, 409)
        complete = self.client.post(reverse('fingerprint-device-complete'),
                                    json.dumps({'request_id': request_id, 'success': True}),
                                    content_type='application/json')
        self.assertEqual(complete.status_code, 409)
        self.biometric.refresh_from_db()
        self.assertTrue(self.biometric.left_finger.name.split('/')[-1].startswith('kept'))
        self.assertFalse(self.biometric.left_finger_template)
        self.assertEqual(FingerprintCaptureRequest.objects.get(pk=request_id).status, 'cancelled')

    def test_normal_capture_and_capture_after_cancel_still_work(self):
        cancelled = self.start()
        self.client.post(reverse('cancel-fingerprint-capture', args=[cancelled]))
        request_id = self.start()
        self.assertNotEqual(request_id, cancelled)
        self.assertEqual(self.client.get(reverse('fingerprint-device-next')).json()['request_id'], request_id)
        self.assertEqual(self.upload_image().status_code, 200, self.upload_image().content)
        self.assertEqual(self.upload_template().status_code, 200)
        complete = self.client.post(reverse('fingerprint-device-complete'),
                                    json.dumps({'request_id': request_id, 'success': True}),
                                    content_type='application/json')
        self.assertEqual(complete.status_code, 200)
        self.biometric.refresh_from_db()
        self.assertFalse(self.biometric.left_finger.name.split('/')[-1].startswith('kept'))
        # The right finger has no capture requests at all, so legacy uploads are unaffected.
        self.assertEqual(self.upload_image('right').status_code, 200)

    def test_completed_capture_is_not_cancelled(self):
        request_id = self.start()
        self.client.get(reverse('fingerprint-device-next'))
        self.client.post(reverse('fingerprint-device-complete'), json.dumps({'request_id': request_id, 'success': True}),
                         content_type='application/json')
        response = self.client.post(reverse('cancel-fingerprint-capture', args=[request_id]))
        self.assertEqual(response.json()['status'], 'completed')

    def test_abandoned_pending_requests_expire_before_scanner_picks_them(self):
        other = Applicant.objects.create(
            lastname='Other', firstname='Wrong', middlename='', age=30, sex='Female', birthdate=date(1996, 1, 2),
            birthplace='Pio Duran', phone='09170000000', status='APPROVED', verification_status='BIOMETRICS_PENDING')
        stale = FingerprintCaptureRequest.objects.create(applicant=other, finger='left', status='pending')
        FingerprintCaptureRequest.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timedelta(minutes=5))
        fresh = self.start()
        self.assertEqual(self.client.get(reverse('fingerprint-device-next')).json()['request_id'], fresh)
        self.assertEqual(FingerprintCaptureRequest.objects.get(pk=stale.pk).status, 'cancelled')

    def test_cancel_requires_staff_post(self):
        request_id = self.start()
        self.assertEqual(self.client.get(reverse('cancel-fingerprint-capture', args=[request_id])).status_code, 405)
        self.client.logout()
        self.client.post(reverse('cancel-fingerprint-capture', args=[request_id]))
        self.assertEqual(FingerprintCaptureRequest.objects.get(pk=request_id).status, 'pending')
        self.client.force_login(self.admin)
        page = self.client.get(reverse('admin-applicant-biometric', args=[self.applicant.pk]))
        self.assertContains(page, 'data-cancel-capture-url="')
