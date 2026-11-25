"""Partial thumbprints are rejected before saving; the officer may accept one after repeated tries."""
import io
import json
import math
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from Applicants.models import Applicant, ApplicantBiometric, Barangay, FingerprintCaptureRequest
from core.fingerprint_quality import assess

WIDTH, HEIGHT = 256, 288


def thumb(top=0.0, bottom=1.0, left=0.0, right=1.0, contrast=100, background=200):
    """Synthetic AS608-like image: ridges inside the given part of the scanner (shares 0-1)."""
    image = Image.new('L', (WIDTH, HEIGHT), background)
    pixels = image.load()
    for y in range(int(top * HEIGHT), int(bottom * HEIGHT)):
        for x in range(int(left * WIDTH), int(right * WIDTH)):
            pixels[x, y] = int(128 + contrast * math.sin((x + y) / 3.0) / 2)
    return image


def upload(image):
    output = io.BytesIO()
    image.save(output, format='BMP')
    return SimpleUploadedFile('finger.bmp', output.getvalue(), content_type='image/bmp')


@override_settings(FINGERPRINT_MIN_COVERAGE=60)
class QualityRuleTests(SimpleTestCase):
    def test_whole_thumb_is_accepted(self):
        result = assess(thumb(0.05, 0.95, 0.1, 0.9))
        self.assertTrue(result['ok'], result)
        self.assertGreaterEqual(result['coverage'], 60)

    def test_partial_thumb_is_rejected(self):
        result = assess(thumb(0.65, 1.0))  # only the bottom of the scanner
        self.assertFalse(result['ok'])
        self.assertIn('partial thumbprint', result['message'])

    def test_lightly_pressed_thumb_is_rejected(self):
        self.assertFalse(assess(thumb(contrast=10))['ok'])  # ridges too faint to count

    def test_thumb_at_the_edge_is_rejected(self):
        result = assess(thumb(0.0, 1.0, 0.0, 0.62))  # enough coverage but crowded to one side
        self.assertFalse(result['ok'])

    def test_wet_or_pressed_thumb_is_rejected(self):
        result = assess(thumb().point(lambda value: value // 5))  # the whole image is nearly black
        self.assertFalse(result['ok'])
        self.assertIn('too dark', result['message'])

    def test_blank_scanner_is_rejected(self):
        self.assertFalse(assess(Image.new('L', (WIDTH, HEIGHT), 128))['ok'])


@override_settings(FINGERPRINT_MIN_COVERAGE=60, FINGERPRINT_PARTIAL_TRIES=3, PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class CaptureFlowTests(TestCase):
    def setUp(self):
        self.officer = get_user_model().objects.create_superuser(username='fpofficer', password='x')
        self.client.force_login(self.officer)
        brgy = Barangay.objects.create(name='Agol')
        self.applicant = Applicant.objects.create(
            lastname='Reyes', firstname='Ana', age=26, sex='Female', birthdate=date(2000, 1, 2), birthplace='X',
            phone='09171234567', brgy=brgy, status='APPROVED')

    def start(self, accept_partial=False):
        data = {'finger': 'left', **({'accept_partial': '1'} if accept_partial else {})}
        response = self.client.post(reverse('start-fingerprint-capture', args=[self.applicant.pk]), data)
        if response.status_code == 200:
            self.client.get(reverse('fingerprint-device-next'))  # the scanner picks it up
        return response

    def send(self, image):
        return self.client.post(reverse('save-fingerprint', args=[self.applicant.pk]),
                                {'finger': 'left', 'fingerprint': upload(image)})

    def status(self, request_id):
        return self.client.get(reverse('fingerprint-capture-status', args=[request_id])).json()

    def test_partial_is_not_saved_and_the_officer_sees_why(self):
        request_id = self.start().json()['request_id']
        response = self.send(thumb(0.7, 1.0))
        self.assertEqual(response.status_code, 422)
        self.assertFalse(ApplicantBiometric.objects.filter(applicant=self.applicant).exclude(left_finger='').exists())
        status = self.status(request_id)
        self.assertEqual(status['status'], 'failed')
        self.assertIn('partial thumbprint', status['message'])
        # the device's own "complete" report does not overwrite the reason
        self.client.post(reverse('fingerprint-device-complete'), json.dumps({'request_id': request_id, 'success': False}),
                         content_type='application/json')
        self.assertIn('partial thumbprint', self.status(request_id)['message'])
        # and the template of that capture is not saved either
        template = self.client.post(reverse('fingerprint-device-upload', args=[self.applicant.pk]),
                                    json.dumps({'finger': 'left', 'template': 'QUJD'}), content_type='application/json')
        self.assertEqual(template.status_code, 409)

    def test_whole_thumb_is_saved_after_a_partial(self):
        self.start(); self.send(thumb(0.7, 1.0))
        self.start()
        self.assertEqual(self.send(thumb(0.05, 0.95, 0.1, 0.9)).status_code, 200)
        self.assertTrue(ApplicantBiometric.objects.get(applicant=self.applicant).left_finger)

    def test_good_thumbprint_is_kept_when_a_recapture_is_partial(self):
        self.start(); self.send(thumb(0.05, 0.95, 0.1, 0.9))
        saved = ApplicantBiometric.objects.get(applicant=self.applicant).left_finger.name
        self.start(); self.send(thumb(0.7, 1.0))
        self.assertEqual(ApplicantBiometric.objects.get(applicant=self.applicant).left_finger.name, saved)

    def test_officer_may_accept_after_three_rejections(self):
        self.assertEqual(self.start(accept_partial=True).status_code, 400)  # not yet
        for _ in range(3):
            request_id = self.start().json()['request_id']
            self.send(thumb(0.7, 1.0))
        self.assertTrue(self.status(request_id)['can_accept_partial'])
        request_id = self.start(accept_partial=True).json()['request_id']
        self.assertEqual(self.send(thumb(0.7, 1.0)).status_code, 200)
        self.assertTrue(ApplicantBiometric.objects.get(applicant=self.applicant).left_finger)
        capture = FingerprintCaptureRequest.objects.get(pk=request_id)
        self.assertTrue(capture.accept_partial)
        self.assertEqual(capture.requested_by, self.officer)
