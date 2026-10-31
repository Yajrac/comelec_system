from datetime import date
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from Applicants.models import (Applicant, Barangay, ApplicantTransferRequest,
    ApplicantReactivationRequest, ApplicantReinstatementRequest)

@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ServiceDocumentTests(TestCase):
    def test_documents_are_retained_replaced_and_required_when_missing(self):
        current = Barangay.objects.create(name='Caratagan')
        destination = Barangay.objects.create(name='Binodegahan')
        admin = get_user_model().objects.create_superuser(username='documentadmin', password='test-password')
        services = [('transfer', ApplicantTransferRequest), ('reactivation', ApplicantReactivationRequest), ('reinstatement', ApplicantReinstatementRequest)]
        for service, model in services:
            for scenario in ['reuse', 'replace', 'missing', 'invalid']:
                with self.subTest(service=service, scenario=scenario):
                    applicant = Applicant.objects.create(lastname='Cruz', firstname='Juan', age=26,
                        sex='Male', birthdate=date(2000, 1, 2), birthplace='Pio Duran', brgy=current,
                        phone='09171234567', is_active=False)
                    if scenario != 'missing':
                        applicant.valid_id_document.save('original.pdf', SimpleUploadedFile('original.pdf', b'%PDF-1.7 original'))
                    original = applicant.valid_id_document.name or ""
                    lookup = self.client.post(reverse(service+'-registration'), {
                        'action': 'find_applicant', 'registration_reference': applicant.registration_reference})
                    if original:
                        self.assertContains(lookup, 'View existing document')
                    payload = {'action': 'submit_'+service, 'applicant_id': applicant.pk,
                        'reason': 'Please process this registration request.', 'new_brgy': destination.pk,
                        'new_municipality': 'Pio Duran', 'new_province': 'Albay'}
                    if scenario in ['replace', 'invalid']:
                        payload['valid_id_document'] = SimpleUploadedFile('new.pdf', b'%PDF-1.7 replacement' if scenario=='replace' else b'wrong contents')
                    response = self.client.post(reverse(service+'-registration'), payload)
                    applicant.refresh_from_db()
                    self.assertEqual(applicant.valid_id_document.name, original)
                    self.assertEqual(applicant.brgy_id, current.pk)
                    self.assertFalse(applicant.is_active)
                    if scenario in ['reuse', 'replace']:
                        self.assertEqual(response.status_code, 302)
                        application = model.objects.get(applicant=applicant)
                        self.assertTrue(application.valid_id_document.storage.exists(application.valid_id_document.name))
                        self.client.force_login(admin)
                        detail = self.client.get(reverse('admin-application-'+service+'-detail', args=[application.pk]))
                        self.assertContains(detail, 'View request document')
                        self.assertContains(detail, 'View original document')
                        self.client.logout()
                        if scenario=='reuse':
                            self.assertEqual(application.valid_id_document.name, original)
                        else:
                            self.assertNotEqual(application.valid_id_document.name, original)
                    else:
                        self.assertEqual(response.status_code, 200)
                        self.assertFalse(model.objects.filter(applicant=applicant).exists())

    def test_active_records_show_modal_without_request_form(self):
        applicant = Applicant.objects.create(lastname='Cruz', firstname='Juan', age=26,
            sex='Male', birthdate=date(2000, 1, 2), birthplace='Pio Duran', phone='09171234567', is_active=True)
        for service in ['reactivation', 'reinstatement']:
            for action in ['find_applicant', 'submit_'+service]:
                with self.subTest(service=service, action=action):
                    response = self.client.post(reverse(service+'-registration'), {
                        'action': action, 'registration_reference': applicant.registration_reference,
                        'applicant_id': applicant.pk,
                    })
                    self.assertContains(response, 'id="pendingCorrectionDialog"')
                    self.assertContains(response, 'already active')
                    self.assertNotContains(response, 'name="action" value="submit_'+service+'"')
        self.assertEqual(ApplicantReactivationRequest.objects.count(), 0)
        self.assertEqual(ApplicantReinstatementRequest.objects.count(), 0)

    def test_pending_transfer_lookup_shows_modal_without_transfer_form(self):
        barangay = Barangay.objects.create(name='Caratagan')
        applicant = Applicant.objects.create(lastname='Cruz', firstname='Juan', age=26,
            sex='Male', birthdate=date(2000, 1, 2), birthplace='Pio Duran', phone='09171234567', brgy=barangay)
        application = ApplicantTransferRequest.objects.create(applicant=applicant, current_brgy=barangay,
            new_brgy=barangay, reason='Test transfer request')
        for status in ['PENDING', 'REVIEW']:
            application.status = status
            application.save(update_fields=['status'])
            response = self.client.post(reverse('transfer-registration'), {
                'action': 'find_applicant', 'registration_reference': applicant.registration_reference,
            })
            self.assertContains(response, 'id="pendingCorrectionDialog"')
            self.assertNotContains(response, 'name="action" value="submit_transfer"')
            self.assertEqual(ApplicantTransferRequest.objects.count(), 1)
