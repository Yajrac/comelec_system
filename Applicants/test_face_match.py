"""New Registration face match: selfie vs ID photo on this server (the face engine is mocked)."""
import io
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from Applicants.face_match import FaceEngineUnavailable, evaluate
from Applicants.models import Applicant, Barangay, FaceMatch
from Applicants.test_document_check import AI_ON, pdf, reading

FACE_ON = dict(AI_ON, FACE_MATCH_ENABLED=True, FACE_MATCH_MAX_DISTANCE=0.60, FACE_MATCH_REJECT_DISTANCE=0.75)
ENGINE = 'Applicants.face_match.read_faces'


def image(color='white', name='selfie.jpg'):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (40, 40), color).save(buffer, 'JPEG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


def faces(distance=0.3, selfie_face=True, document_face=True):
    return {'selfie_has_face': selfie_face, 'document_has_face': document_face,
            'distance': distance if selfie_face and document_face else None, 'engine': 'deepface-arcface-opencv-v1'}


@override_settings(FACE_MATCH_MAX_DISTANCE=0.60, FACE_MATCH_REJECT_DISTANCE=0.75)
class FaceRuleTests(SimpleTestCase):
    def test_distance_bands(self):
        self.assertEqual(evaluate(faces(0.30)), 'matched')
        self.assertEqual(evaluate(faces(0.60)), 'matched')
        self.assertEqual(evaluate(faces(0.66)), 'unsure')        # in between: the office compares
        self.assertEqual(evaluate(faces(0.75)), 'not_matched')
        self.assertEqual(evaluate(faces(0.85)), 'not_matched')   # e.g. a friend's selfie with your ID
        self.assertEqual(evaluate(faces(selfie_face=False)), 'no_face')
        self.assertEqual(evaluate(faces(document_face=False)), 'unsure')

    def test_similarity_for_officers(self):
        self.assertEqual(FaceMatch(ai_result=faces(0.153)).similarity, 85)
        self.assertIsNone(FaceMatch(ai_result={}).similarity)


@override_settings(**FACE_ON)
@patch('Applicants.document_check.ask_gemini', return_value=dict(reading(), document_code='PHILSYS'))
class FaceFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brgy = Barangay.objects.create(name='Agol')

    def check(self, photo=None, document=None, id_type='PHILSYS'):
        return self.client.post('/face-check/', {'photo': photo or image(), 'valid_id_type': id_type,
                                                 'valid_id_document': document or image('gray', 'id.jpg')})

    def registration(self, photo=None, **extra):
        data = {'lastname': 'Diaz', 'firstname': 'Maria Althea', 'middlename': 'Palacio', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Pio Duran', 'brgy': self.brgy.pk,
                'phone': '09171234567', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_document': image('gray', 'id.jpg'), 'valid_id_type': 'PHILSYS',
                'photo': photo or image()}
        data.update(extra)
        return {key: value for key, value in data.items() if value is not None}

    @patch(ENGINE, return_value=faces(0.3))
    def test_match_is_read_once(self, engine, _doc):
        self.assertEqual(self.check().json()['status'], 'matched')
        self.assertEqual(self.check().json()['status'], 'matched')
        self.assertEqual(engine.call_count, 1)

    @patch(ENGINE)
    def test_birth_certificate_is_not_compared(self, engine, _doc):
        self.assertEqual(self.check(id_type='PSA_BIRTH_CERTIFICATE').json()['status'], 'not_applicable')
        engine.assert_not_called()

    @patch(ENGINE)
    def test_pdf_document_is_left_to_the_office(self, engine, _doc):
        self.assertEqual(self.check(document=pdf()).json()['status'], 'unavailable')
        engine.assert_not_called()

    @patch(ENGINE, return_value=faces(0.85))
    def test_second_different_selfie_is_flagged_not_blocked(self, engine, _doc):
        self.assertEqual(self.check(image('white')).json()['status'], 'not_matched')
        self.assertEqual(self.check(image('black')).json()['status'], 'flagged')

    @patch(ENGINE, return_value=faces(selfie_face=False))
    def test_no_face_asks_for_a_retake(self, engine, _doc):
        body = self.check().json()
        self.assertEqual(body['status'], 'no_face')
        self.assertIn('Retake your selfie', body['message'])

    @patch(ENGINE, side_effect=FaceEngineUnavailable('error'))
    def test_engine_problem_lets_the_applicant_continue(self, engine, _doc):
        self.assertEqual(self.check().json()['status'], 'unavailable')
        response = self.client.post('/api/new-registration/', self.registration())
        self.assertEqual(response.status_code, 201, response.content)

    @patch(ENGINE, return_value=faces(0.85))
    def test_mismatch_blocks_the_submission(self, engine, _doc):
        response = self.client.post('/api/new-registration/', self.registration())
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not match the photo on your ID', response.json()['error'])
        self.assertFalse(Applicant.objects.exists())

    @patch(ENGINE, return_value=faces(0.2))
    def test_match_is_linked_and_shown_to_the_officer(self, engine, _doc):
        response = self.client.post('/api/new-registration/', self.registration())
        self.assertEqual(response.status_code, 201, response.content)
        applicant = Applicant.objects.get()
        self.assertEqual(FaceMatch.objects.get(record_id=applicant.pk).status, 'matched')
        self.client.force_login(get_user_model().objects.create_superuser(username='faceofficer', password='x'))
        page = self.client.get(f'/comelec/admin-applications/new/{applicant.pk}/')
        self.assertContains(page, 'Likely the same person')
        self.assertContains(page, 'Similarity: <strong>80%</strong>')
        self.assertContains(page, 'face-match-compare')

    @patch(ENGINE, return_value=faces(0.85))
    def test_walk_in_officer_can_override(self, engine, _doc):
        self.client.force_login(get_user_model().objects.create_superuser(username='facewalkin', password='x'))
        self.client.post('/comelec/walk-in/new/', self.registration(officer_verified='1'))
        applicant = Applicant.objects.get()
        self.assertEqual(FaceMatch.objects.get(record_id=applicant.pk).status, 'override')

    def test_page_shows_the_notice_without_a_consent_box(self, _doc):
        html = self.client.get('/new-registration/').content.decode()
        self.assertIn('id="selfieLocked"', html)
        self.assertNotIn('name="face_consent"', html)
        self.assertIn('data-face-match="1"', html)
        self.assertIn('js/face-match.js', html)


@override_settings(**AI_ON)
class FaceMatchOffTests(TestCase):
    @patch(ENGINE)
    def test_off_by_default_compares_nothing(self, engine):
        body = self.client.post('/face-check/', {'photo': image(), 'valid_id_document': image('gray', 'id.jpg'),
                                                 'valid_id_type': 'PHILSYS'}).json()
        self.assertEqual(body['status'], 'disabled')
        engine.assert_not_called()
        html = self.client.get('/new-registration/').content.decode()
        self.assertIn('id="selfieLocked"', html)  # document first still applies
        self.assertNotIn('data-face-match', html)

    def test_service_requests_are_unchanged(self):
        self.assertNotIn('id="selfieLocked"', self.client.get('/update-registration/').content.decode())


class FaceEngineSetupTests(SimpleTestCase):
    def test_nothing_is_sent_to_an_outside_service(self):
        source = (Path(settings.BASE_DIR) / 'Applicants/face_match.py').read_text(encoding='utf-8')
        self.assertNotIn('genai', source)
        self.assertIn('from deepface import DeepFace', source)

    def test_browser_checks_light_before_sending(self):
        script = (Path(settings.BASE_DIR) / 'static/js/face-match.js').read_text(encoding='utf-8')
        for text in ('const DARK = 70', 'const DARK_TRIES = 3', 'Your selfie is too dark.',
                     'will be automatically compared with the photo on your'):
            self.assertIn(text, script)

    def test_model_files_stay_out_of_git(self):
        self.assertIn('/face_models/', (Path(settings.BASE_DIR) / '.gitignore').read_text(encoding='utf-8'))
        self.assertIn('deepface==', (Path(settings.BASE_DIR) / 'requirements.txt').read_text(encoding='utf-8'))
