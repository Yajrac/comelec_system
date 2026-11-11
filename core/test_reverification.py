"""An approved service request archives old biometrics and requires a new capture and receipt."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from Applicants.models import (AcknowledgmentReceipt, Applicant, ApplicantBiometric, ApplicantTransferRequest,
                               Barangay, BiometricHistory)

CAPTURE_FILES = ("left_finger", "right_finger", "applicant_signature", "applicant_signature_2", "applicant_signature_3")


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0, STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
@patch('core.views.send_approval_sms', return_value=True)
class ReverificationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username='reverifyadmin', password='test-password')
        self.client.force_login(self.admin)
        self.old_brgy = Barangay.objects.create(name='Agol')
        self.new_brgy = Barangay.objects.create(name='Binodegahan')
        self.applicant = Applicant.objects.create(
            lastname='Santos', firstname='Aiza', middlename='Ybanez', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='Pio Duran', phone='09171234567', brgy=self.old_brgy,
            status='APPROVED', verification_status='VERIFIED', is_active=True)
        self.biometric = ApplicantBiometric.objects.create(applicant=self.applicant)
        self.capture(self.biometric, 'old')

    def capture(self, biometric, tag):
        for name in CAPTURE_FILES:
            getattr(biometric, name).save(f'{tag}-{name}.png', ContentFile(b'png'), save=False)
        biometric.save()

    def approve_transfer(self):
        transfer = ApplicantTransferRequest.objects.create(
            applicant=self.applicant, current_brgy=self.old_brgy, new_brgy=self.new_brgy, status='PENDING')
        response = self.client.post(reverse('admin-application-action', args=['transfer', transfer.pk, 'approve']))
        self.assertRedirects(response, reverse('admin-applicant-biometric', args=[self.applicant.pk]),
                             fetch_redirect_response=False)
        return transfer

    def test_full_reverification_round(self, sms):
        # First verification round issues the NEW receipt.
        from core.biometric_state import sync_completion
        self.assertTrue(sync_completion(self.biometric))
        self.client.get(reverse('acknowledgment-receipt', args=[self.applicant.pk]))
        first_receipt = AcknowledgmentReceipt.objects.get()
        old_names = {name: getattr(self.biometric, name).name for name in CAPTURE_FILES}

        transfer = self.approve_transfer()

        # Old capture is archived (files untouched) and the applicant must be captured again.
        self.applicant.refresh_from_db()
        self.biometric.refresh_from_db()
        self.assertEqual(self.applicant.verification_status, 'BIOMETRICS_PENDING')
        self.assertEqual(self.applicant.brgy, self.new_brgy)
        self.assertFalse(self.biometric.completed)
        self.assertTrue(all(not getattr(self.biometric, name) for name in CAPTURE_FILES))
        self.assertEqual((self.biometric.application_type, self.biometric.application_request_id), ('TRANSFER', transfer.pk))
        archived = BiometricHistory.objects.get()
        self.assertEqual({name: getattr(archived, name).name for name in CAPTURE_FILES}, old_names)
        self.assertTrue(all(getattr(archived, name).storage.exists(old_names[name]) for name in CAPTURE_FILES))
        self.assertEqual((archived.application_type, archived.replaced_by_type, archived.replaced_by_request_id),
                         ('NEW', 'TRANSFER', transfer.pk))
        self.assertTrue(archived.was_completed)

        # Still listed on the Applicants page, flagged as awaiting new biometrics.
        listing = self.client.get(reverse('admin-applicants'))
        self.assertContains(listing, 'Biometrics Pending')
        self.assertContains(listing, reverse('admin-applicant-biometric', args=[self.applicant.pk]))
        self.assertContains(self.client.get(reverse('admin-applicant-biometric', args=[self.applicant.pk])),
                            'New biometrics required: Transfer #')

        # Finish is refused until the new capture is complete.
        finish = reverse('admin-finish-verification', args=[self.applicant.pk])
        self.assertRedirects(self.client.post(finish), reverse('admin-applicant-biometric', args=[self.applicant.pk]),
                             fetch_redirect_response=False)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.verification_status, 'BIOMETRICS_PENDING')

        self.capture(self.biometric, 'new')
        self.assertRedirects(self.client.post(finish), reverse('admin-applicants'), fetch_redirect_response=False)
        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.verification_status, 'VERIFIED')
        self.assertContains(self.client.get(reverse('admin-applicants')), 'Verified')

        # The new round gets its own receipt; the first one stays and can be reopened.
        response = self.client.get(reverse('acknowledgment-receipt', args=[self.applicant.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AcknowledgmentReceipt.objects.count(), 2)
        second = AcknowledgmentReceipt.objects.exclude(pk=first_receipt.pk).get()
        self.assertEqual((second.application_type, second.application_request_id), ('TRANSFER', transfer.pk))
        self.assertIn('TRANSFER', second.details['application_type'])
        self.client.get(reverse('acknowledgment-receipt', args=[self.applicant.pk]))
        self.assertEqual(AcknowledgmentReceipt.objects.count(), 2)
        reopened = self.client.get(reverse('acknowledgment-receipt-issued', args=[self.applicant.pk, first_receipt.pk]))
        self.assertEqual(reopened.context['receipt_values']['application_no'], first_receipt.application_number)

        detail = self.client.get(reverse('admin-applicant-detail', args=[self.applicant.pk]))
        self.assertContains(detail, 'Previous Biometrics')
        self.assertContains(detail, first_receipt.application_number)
        self.assertContains(detail, second.application_number)
        self.assertEqual(len(detail.context['previous_biometrics']), 1)

    def test_pending_new_registration_is_not_listed_and_finish_requires_post(self, sms):
        self.client.post(reverse('admin-finish-verification', args=[self.applicant.pk]))
        newcomer = Applicant.objects.create(
            lastname='Newcomer', firstname='Pedro', middlename='', age=30, sex='Male', birthdate=date(1996, 1, 2),
            birthplace='Pio Duran', phone='09170000000', brgy=self.old_brgy, status='APPROVED',
            verification_status='BIOMETRICS_PENDING', is_active=True)
        ApplicantBiometric.objects.create(applicant=newcomer)
        listing = self.client.get(reverse('admin-applicants'))
        self.assertNotContains(listing, 'Newcomer')
        self.assertContains(listing, 'Santos')
        self.assertEqual(self.client.get(reverse('admin-finish-verification', args=[newcomer.pk])).status_code, 405)

    def test_receipt_for_other_applicant_is_not_reachable(self, sms):
        other = Applicant.objects.create(
            lastname='Other', firstname='Ana', middlename='', age=30, sex='Female', birthdate=date(1996, 1, 2),
            birthplace='Pio Duran', phone='09170000001', status='APPROVED', verification_status='VERIFIED')
        receipt = AcknowledgmentReceipt.objects.create(applicant=other, application_number='123456789012',
                                                      details={'application_type': 'NEW'}, issued_by=self.admin)
        url = reverse('acknowledgment-receipt-issued', args=[self.applicant.pk, receipt.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
