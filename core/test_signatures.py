import base64
import json
from datetime import date
from io import BytesIO

from PIL import Image, ImageDraw
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from Applicants.models import Applicant, ApplicantBiometric, SignatureSession
from core.biometric_state import sync_completion


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ThreeSignatureTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('signature-admin', 'admin@example.com', 'test-password')
        self.applicant = Applicant.objects.create(firstname='Sample', lastname='Applicant', middlename='', age=26,
            birthdate=date(2000,1,1), birthplace='Pio Duran', sex='Male', phone='09171234567',
            email='signature@example.com', father='Sample Father', mother='Sample Mother', status='APPROVED')
        self.biometric = ApplicantBiometric.objects.create(applicant=self.applicant)
        image = Image.new('RGB', (240,100), 'white')
        ImageDraw.Draw(image).line([(20,70),(70,20),(100,65),(190,35)], fill='black', width=3)
        output = BytesIO(); image.save(output, format='PNG')
        self.png = output.getvalue()
        self.signature = 'data:image/png;base64,' + base64.b64encode(self.png).decode()
        self.client.force_login(self.admin)

    def start(self, slot=None):
        data = {} if slot is None else {'signature_slot': slot}
        return self.client.post(reverse('start-signature-session', args=[self.applicant.pk]), json.dumps(data), content_type='application/json')

    def upload(self, session, **extra):
        return self.client.post(reverse('complete-signature-session'), json.dumps({'session_id':session,'signature':self.signature, **extra}), content_type='application/json')

    def test_legacy_device_defaults_to_first_slot(self):
        response = self.start()
        self.assertEqual(response.status_code, 200)
        session = response.json()['session_id']
        self.assertEqual(response.json()['signature_slot'], 1)
        # Original device posts only session_id and signature.
        self.assertEqual(self.upload(session).status_code, 200)
        self.biometric.refresh_from_db()
        self.assertTrue(self.biometric.applicant_signature)
        self.assertFalse(self.biometric.applicant_signature_2)
        self.assertFalse(self.biometric.completed)

    def test_apk_session_upload_is_single_use(self):
        data = self.start(2).json()
        self.assertNotIn('signing_url', data)
        self.client.logout()
        self.assertEqual(self.upload(data['session_id']).status_code, 200)
        self.assertEqual(self.upload(data['session_id']).status_code, 400)

    def test_device_pairing_is_single_use_scoped_and_revocable(self):
        code = self.client.post(reverse('signature-create-pairing')).json()['code']
        claim_url = reverse('signature-claim-pairing')
        device = self.client_class()
        claim = device.post(claim_url, json.dumps({'code': code}), content_type='application/json')
        self.assertEqual(claim.status_code, 200)
        token = claim.json()['token']
        self.assertEqual(device.post(claim_url, json.dumps({'code': code}), content_type='application/json').status_code, 400)
        url = reverse('signature-paired-request')
        headers = {'HTTP_AUTHORIZATION': 'Bearer ' + token}
        self.assertEqual(device.get(url).status_code, 401)
        self.assertIsNone(device.get(url, **headers).json()['session'])
        session = self.start(2).json()['session_id']
        response = device.get(url, **headers)
        self.assertEqual(response.json()['session']['session_id'], session)
        self.assertEqual(response['Cache-Control'], 'no-store')
        other = get_user_model().objects.create_superuser('other-signing-officer', 'other@example.com', 'password')
        SignatureSession.objects.create(officer=other, applicant=self.applicant, signature_slot=3)
        self.assertEqual(device.get(url, **headers).json()['session']['session_id'], session)
        self.upload(session)
        self.assertIsNone(device.get(url, **headers).json()['session'])
        self.client.post(reverse('signature-create-pairing'))
        self.assertEqual(device.get(url, **headers).status_code, 401)

    def test_expired_pairing_and_non_admin_are_rejected(self):
        from Applicants.models import SignatureDevicePairing
        from django.utils import timezone
        from datetime import timedelta
        code = self.client.post(reverse('signature-create-pairing')).json()['code']
        SignatureDevicePairing.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        response = self.client.post(reverse('signature-claim-pairing'), json.dumps({'code': code}), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.admin.is_superuser = False
        self.admin.save()
        self.assertEqual(self.client.post(reverse('signature-create-pairing')).status_code, 403)

    def test_three_samples_and_two_fingers_required(self):
        self.biometric.left_finger.save('left.png', ContentFile(self.png))
        self.biometric.right_finger.save('right.png', ContentFile(self.png))
        self.assertFalse(sync_completion(self.biometric))
        for slot in (1,2,3):
            response = self.upload(self.start(slot).json()['session_id'])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['biometrics_completed'], slot == 3)
        self.biometric.refresh_from_db(); self.applicant.refresh_from_db()
        self.assertTrue(self.biometric.completed)
        self.assertEqual(self.applicant.verification_status, 'VERIFIED')
        response = self.client.get(reverse('print-slip-account', args=[self.applicant.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Applicant signature sample 3')


    def test_signatures_without_fingerprints_are_incomplete(self):
        for slot in (1,2,3): self.upload(self.start(slot).json()['session_id'])
        self.biometric.refresh_from_db()
        self.assertFalse(self.biometric.completed)

    def test_retake_preserves_other_slots_and_original_file(self):
        for slot in (1,2,3): self.upload(self.start(slot).json()['session_id'])
        self.biometric.refresh_from_db()
        first = self.biometric.applicant_signature.name
        second = self.biometric.applicant_signature_2.name
        third = self.biometric.applicant_signature_3.name
        self.upload(self.start(2).json()['session_id'], signature_slot=3)
        self.biometric.refresh_from_db()
        self.assertEqual(self.biometric.applicant_signature.name, first)
        self.assertEqual(self.biometric.applicant_signature_3.name, third)
        self.assertNotEqual(self.biometric.applicant_signature_2.name, second)
        self.assertTrue(self.biometric.applicant_signature_2.storage.exists(second))

    def test_cancelled_session_cannot_overwrite(self):
        first = self.start(1).json()['session_id']
        self.start(2)
        self.assertEqual(self.upload(first).status_code, 400)
        self.biometric.refresh_from_db()
        self.assertFalse(self.biometric.applicant_signature)

    def test_repeated_completion_rejected(self):
        session = self.start(1).json()['session_id']
        self.assertEqual(self.upload(session).status_code, 200)
        self.assertEqual(self.upload(session).status_code, 400)

    def test_invalid_slot_and_bad_png_rejected(self):
        for slot in (0,4,True,'wrong'):
            self.assertEqual(self.start(slot).status_code, 400)
        session = self.start(1).json()['session_id']
        self.signature = 'data:image/png;base64,' + base64.b64encode(b'not an image').decode()
        self.assertEqual(self.upload(session).status_code, 400)
        self.assertEqual(SignatureSession.objects.get(session_id=session).status, 'WAITING')

    def test_waiting_and_status_responses_include_slot(self):
        session = self.start(3).json()['session_id']
        self.assertEqual(self.client.get(reverse('get-waiting-signature-session')).json()['session']['signature_slot'], 3)
        self.upload(session)
        response = self.client.get(reverse('signature-session-status',args=[session]))
        self.assertTrue(response.json()['signature_captured'])
        self.assertEqual(response.json()['signature_slot'], 3)

    def test_admin_page_has_three_controls_and_incomplete_print_redirect(self):
        response = self.client.get(reverse('admin-applicant-biometric',args=[self.applicant.pk]))
        self.assertContains(response, 'js/fingerprint-capture.js')
        self.assertContains(response, 'data-start-capture-url="' + reverse('start-fingerprint-capture', args=[self.applicant.pk]) + '"')
        self.assertContains(response, 'data-left-image="false"')
        self.assertNotContains(response, 'document.addEventListener("DOMContentLoaded"')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count('data-signature-slot='), 3)
        self.assertIn(b'signature-capture.js', response.content)
        self.assertEqual(self.client.get(reverse('print-slip-account',args=[self.applicant.pk])).status_code,302)

    def test_non_admin_cannot_start_capture(self):
        self.admin.is_superuser = False; self.admin.save()
        self.assertEqual(self.start(1).status_code,403)

    def test_missing_file_blocks_completion_and_printing(self):
        self.biometric.left_finger.save('left.png', ContentFile(self.png))
        self.biometric.right_finger.save('right.png', ContentFile(self.png))
        for slot in (1,2,3): self.upload(self.start(slot).json()['session_id'])
        self.biometric.refresh_from_db()
        self.biometric.applicant_signature_2.storage.delete(self.biometric.applicant_signature_2.name)
        self.assertFalse(sync_completion(self.biometric))
        self.assertEqual(self.client.get(reverse('print-slip-account', args=[self.applicant.pk])).status_code, 302)

    def test_cancel_preserves_saved_sample(self):
        self.upload(self.start(1).json()['session_id'])
        self.biometric.refresh_from_db()
        before = self.biometric.applicant_signature.name
        session = self.start(1).json()['session_id']
        response = self.client.post(reverse('cancel-signature-session', args=[session]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.upload(session).status_code, 400)
        self.biometric.refresh_from_db()
        self.assertEqual(self.biometric.applicant_signature.name, before)
