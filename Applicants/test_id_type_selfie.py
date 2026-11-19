"""Document type before uploading, a required selfie, and no "AI" wording for users."""
import io
import re
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from Applicants.models import Applicant, Barangay


def selfie():
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (40, 40), 'white').save(buffer, 'JPEG')
    return SimpleUploadedFile('selfie.jpg', buffer.getvalue(), content_type='image/jpeg')


@override_settings(REQUIRE_ID_TYPE_AND_SELFIE=True, PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class IdTypeAndSelfieTests(TestCase):
    def setUp(self):
        self.brgy = Barangay.objects.create(name='Binodegahan')

    def form(self, **extra):
        data = {'lastname': 'Reyes', 'firstname': 'Ana', 'middlename': '', 'birthdate': '2000-01-02',
                'sex': 'Female', 'civil_status': 'Single', 'birthplace': 'Legazpi', 'brgy': self.brgy.pk,
                'phone': '09170000000', 'email': '', 'pwd_status': 'NO', 'citizenship_status': 'BY_BIRTH',
                'father': '', 'mother': '', 'valid_id_type': 'PHILSYS', 'photo': selfie(),
                'valid_id_document': SimpleUploadedFile('id.pdf', b'%PDF-1.7 test', content_type='application/pdf')}
        data.update(extra)
        return {key: value for key, value in data.items() if value is not None}

    def test_form_lists_the_accepted_documents(self):
        html = self.client.get('/new-registration/').content.decode()
        self.assertIn('name="valid_id_type"', html)
        for label in ('National ID (PhilSys)', 'PSA Birth Certificate', 'PRC License'):
            self.assertIn(label, html)
        self.assertIn('Not accepted: Student ID', html)
        self.assertNotIn('Upload Photo or Selfie (optional)', html)
        self.assertIn('Take a selfie', html)

    def test_document_type_is_required(self):
        response = self.client.post('/new-registration/', self.form(valid_id_type=None))
        self.assertContains(response, 'Choose the type of document you are uploading.')
        self.assertFalse(Applicant.objects.exists())

    def test_unknown_document_type_is_rejected(self):
        self.client.post('/new-registration/', self.form(valid_id_type='STUDENT_ID'))
        self.assertFalse(Applicant.objects.exists())

    def test_selfie_is_required(self):
        response = self.client.post('/new-registration/', self.form(photo=None))
        self.assertContains(response, 'Take a selfie before submitting.')
        self.assertFalse(Applicant.objects.exists())

    def test_document_type_is_saved(self):
        self.client.post('/new-registration/', self.form(valid_id_type='PSA_BIRTH_CERTIFICATE'))
        applicant = Applicant.objects.get()
        self.assertEqual(applicant.valid_id_type, 'PSA_BIRTH_CERTIFICATE')
        self.assertEqual(applicant.get_valid_id_type_display(), 'PSA Birth Certificate')

    def test_walk_in_officer_may_upload_a_photo(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='walkinphoto', password='x'))
        html = self.client.get('/comelec/walk-in/new/').content.decode()
        self.assertIn('Upload photo (walk-in, when no camera is available)', html)

    def test_officer_sees_selected_document_type(self):
        applicant = Applicant.objects.create(
            lastname='Reyes', firstname='Ana', age=26, sex='Female', birthdate=date(2000, 1, 2),
            birthplace='Legazpi', phone='09170000000', brgy=self.brgy, valid_id_type='POSTAL',
            valid_id_document=SimpleUploadedFile('id.pdf', b'%PDF-1.7 test', content_type='application/pdf'))
        self.client.force_login(get_user_model().objects.create_superuser(username='officerid', password='x'))
        response = self.client.get(f'/comelec/admin-applications/new/{applicant.pk}/')
        self.assertContains(response, 'Document verification:')
        self.assertContains(response, 'Postal ID')

    def test_pages_do_not_mention_ai(self):
        for url in ('/new-registration/', '/check-status/'):
            text = re.sub(r'<script.*?</script>|<style.*?</style>|<[^>]+>', ' ',
                          self.client.get(url).content.decode(), flags=re.S)
            self.assertNotRegex(text, r'\bAI\b', url)
