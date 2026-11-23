"""New Registration face match: selfie vs ID photo (service mocked; never called for real)."""
import io
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from Applicants.document_check import DocumentAIUnavailable
from Applicants.face_match import evaluate
from Applicants.models import Applicant, Barangay, FaceMatch
from Applicants.test_document_check import AI_ON, pdf, reading

FACE_ON = dict(AI_ON, FACE_MATCH_ENABLED=True)


def selfie(color='white'):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (40, 40), color).save(buffer, 'JPEG')
    return SimpleUploadedFile('selfie.jpg', buffer.getvalue(), content_type='image/jpeg')


def answer(same='yes', selfie_face=True, document_face=True):
    return {'selfie_has_face': selfie_face, 'document_has_face': document_face, 'same_person': same}


class FaceRuleTests(SimpleTestCase):
    def test_rules(self):
        self.assertEqual(evaluate(answer()), 'matched')
        self.assertEqual(evaluate(answer('no')), 'not_matched')
        self.assertEqual(evaluate(answer('unsure')), 'unsure')
        self.assertEqual(evaluate(answer(selfie_face=False)), 'no_face')
        self.assertEqual(evaluate(answer('no', document_face=False)), 'unsure')
        self.assertEqual(evaluate(dict(answer(), selfie_is_clear=False)), 'unclear')


@override_settings(**FACE_ON)
@patch('Applicants.document_check.ask_gemini', return_value=dict(reading(), document_code='PHILSYS'))
class FaceFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brgy = Barangay.objects.create(name='Agol')

    def check(self, photo=None, document=None, id_type='PHILSYS', consent=True):
        data = {'photo': photo or selfie(), 'valid_id_document': document or pdf(), 'valid_id_type': id_type}
        if consent:
            data['face_consent'] = '1'
        return self.client.post('/face-check/', data)

    def registration(self, photo=None, **extra):
        data = {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': self.brgy.pk,
                'phone': '09171234567', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_document': pdf(), 'valid_id_type': 'PHILSYS',
                'photo': photo or selfie(), 'face_consent': '1'}
        data.update(extra)
        return {key: value for key, value in data.items() if value is not None}

    @patch('Applicants.face_match.ask_gemini', return_value=answer())
    def test_match_is_read_once(self, ask, _doc):
        self.assertEqual(self.check().json()['status'], 'matched')
        self.assertEqual(self.check().json()['status'], 'matched')
        self.assertEqual(ask.call_count, 1)

    @patch('Applicants.face_match.ask_gemini')
    def test_birth_certificate_is_not_compared(self, ask, _doc):
        body = self.check(id_type='PSA_BIRTH_CERTIFICATE', consent=False).json()
        self.assertEqual(body['status'], 'not_applicable')
        ask.assert_not_called()

    @patch('Applicants.face_match.ask_gemini', return_value=answer())
    def test_no_consent_box_is_needed(self, ask, _doc):
        self.assertEqual(self.check(consent=False).json()['status'], 'matched')

    @patch('Applicants.face_match.ask_gemini', return_value=dict(answer(), selfie_is_clear=False))
    def test_dark_or_blurry_selfie_must_be_retaken_then_is_flagged(self, ask, _doc):
        body = self.check(selfie('white')).json()
        self.assertEqual(body['status'], 'unclear')
        self.assertIn('too dark or blurry', body['message'])
        self.assertEqual(self.check(selfie('black')).json()['status'], 'flagged')

    @patch('Applicants.face_match.ask_gemini', return_value=answer('no'))
    def test_second_different_selfie_is_flagged_not_blocked(self, ask, _doc):
        self.assertEqual(self.check(selfie('white')).json()['status'], 'not_matched')
        self.assertEqual(self.check(selfie('black')).json()['status'], 'flagged')

    @patch('Applicants.face_match.ask_gemini', return_value=answer(selfie_face=False))
    def test_no_face_asks_for_a_retake(self, ask, _doc):
        body = self.check().json()
        self.assertEqual(body['status'], 'no_face')
        self.assertIn('Retake your selfie', body['message'])

    @patch('Applicants.face_match.ask_gemini', side_effect=DocumentAIUnavailable('error'))
    def test_service_down_lets_the_applicant_continue(self, ask, _doc):
        self.assertEqual(self.check().json()['status'], 'unavailable')
        response = self.client.post('/api/new-registration/', self.registration())
        self.assertEqual(response.status_code, 201, response.content)

    @patch('Applicants.face_match.ask_gemini', return_value=answer('no'))
    def test_mismatch_blocks_the_submission(self, ask, _doc):
        response = self.client.post('/api/new-registration/', self.registration())
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not match the photo on your ID', response.json()['error'])
        self.assertFalse(Applicant.objects.exists())

    @patch('Applicants.face_match.ask_gemini', return_value=answer())
    def test_match_is_linked_and_shown_to_the_officer(self, ask, _doc):
        response = self.client.post('/api/new-registration/', self.registration())
        self.assertEqual(response.status_code, 201, response.content)
        applicant = Applicant.objects.get()
        self.assertEqual(FaceMatch.objects.get(record_id=applicant.pk).status, 'matched')
        self.client.force_login(get_user_model().objects.create_superuser(username='faceofficer', password='x'))
        page = self.client.get(f'/comelec/admin-applications/new/{applicant.pk}/')
        self.assertContains(page, 'Face matches the ID')
        self.assertContains(page, 'face-match-compare')

    @patch('Applicants.face_match.ask_gemini', return_value=answer('no'))
    def test_walk_in_officer_can_override(self, ask, _doc):
        self.client.force_login(get_user_model().objects.create_superuser(username='facewalkin', password='x'))
        self.client.post('/comelec/walk-in/new/', self.registration(officer_verified='1'))
        applicant = Applicant.objects.get()
        self.assertEqual(FaceMatch.objects.get(record_id=applicant.pk).status, 'override')

    def test_page_shows_the_document_first_note_without_a_consent_box(self, _doc):
        html = self.client.get('/new-registration/').content.decode()
        self.assertIn('id="selfieLocked"', html)
        self.assertNotIn('name="face_consent"', html)
        self.assertIn('data-face-match="1"', html)
        self.assertIn('js/face-match.js', html)


@override_settings(**AI_ON)
class FaceMatchOffTests(TestCase):
    def test_off_by_default_sends_nothing(self):
        self.assertEqual(self.client.post('/face-check/', {'photo': selfie(), 'valid_id_document': pdf(),
                                                            'valid_id_type': 'PHILSYS'}).json()['status'], 'disabled')
        html = self.client.get('/new-registration/').content.decode()
        self.assertIn('id="selfieLocked"', html)          # document first still applies
        self.assertNotIn('data-face-match', html)

    def test_service_requests_are_unchanged(self):
        html = self.client.get('/update-registration/').content.decode()
        self.assertNotIn('id="selfieLocked"', html)


class SelfieLightTests(SimpleTestCase):
    def test_browser_checks_light_before_sending(self):
        from pathlib import Path
        from django.conf import settings
        script = (Path(settings.BASE_DIR) / 'static/js/face-match.js').read_text(encoding='utf-8')
        for text in ('const DARK = 70', 'const DARK_TRIES = 3', 'Your selfie is too dark.',
                     'will be automatically compared with the photo on your'):
            self.assertIn(text, script)
        self.assertNotIn('face_consent', script)
