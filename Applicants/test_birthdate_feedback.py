"""Birthdate year limits: shown while typing (segmented-date.js) and enforced by the server."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings

from Applicants.models import Applicant, Barangay


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class BirthdateFeedbackTests(TestCase):
    def test_server_rejects_years_before_1900(self):
        brgy = Barangay.objects.create(name='Agol')
        response = self.client.post('/api/new-registration/', {
            'lastname': 'Reyes', 'firstname': 'Ana', 'middlename': '', 'birthdate': '1222-07-13', 'sex': 'Female',
            'civil_status': 'Single', 'birthplace': 'X', 'brgy': brgy.pk, 'phone': '09170000000', 'email': '',
            'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH', 'father': '', 'mother': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('birth year from 1900', response.json()['errors']['birthdate'])
        self.assertFalse(Applicant.objects.exists())

    def test_form_script_shows_date_problems_while_typing(self):
        script = (Path(settings.BASE_DIR) / 'static/js/segmented-date.js').read_text(encoding='utf-8')
        self.assertIn('Enter a valid birth year from 1900', script)
        self.assertIn("wrapper.classList.toggle('is-invalid'", script)
        self.assertIn('year.validity.customError', script)


class DocumentTypeWordingTests(TestCase):
    """The upload names the chosen document and shows one message when it is missing."""

    def script(self, name):
        return (Path(settings.BASE_DIR) / 'static/js' / name).read_text(encoding='utf-8')

    def test_label_tip_and_message_follow_the_type(self):
        script = self.script('valid-id-type.js')
        for text in ('Upload your ${name}', 'or take a photo of it.', 'Make sure your name is readable.',
                     "'government-issued ID'", 'file.dataset.requiredMessage'):
            self.assertIn(text, script)
        self.assertIn('Take a photo of your ${name}', self.script('document-camera.js'))

    @override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                                 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
    def test_new_registration_shows_a_single_error(self):
        html = self.client.get('/new-registration/').content.decode()
        start = html.index('id="valid_id_document"')
        self.assertIn('data-own-error="1"', html[start:start + 600])
        self.assertIn('if (input.dataset.ownError) return', self.script('input-validation.js'))
        self.assertIn('input.dataset.requiredMessage ||', self.script('pages/applicant-forms-new_registration-1.js'))
