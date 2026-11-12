"""Deleting from the Applications list removes only the clicked record, after typing DELETE."""
from datetime import date

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from Applicants.models import (AcknowledgmentReceipt, Applicant, ApplicantBiometric, ApplicantTransferRequest,
                               Barangay, BiometricHistory)


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DeleteApplicationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(username='deladmin', password='test-password')
        self.client.force_login(self.admin)
        self.brgy = Barangay.objects.create(name='Agol')

    def applicant(self, name, status='PENDING'):
        return Applicant.objects.create(lastname=name, firstname='Juan', middlename='', age=30, sex='Male',
                                        birthdate=date(1996, 1, 2), birthplace='X', phone='09171234567',
                                        brgy=self.brgy, status=status)

    def delete(self, kind, pk, confirm='DELETE'):
        return self.client.post(reverse('delete-application', args=[kind, pk]), {'confirm_text': confirm})

    def test_deleting_a_request_never_deletes_the_applicant_with_the_same_id(self):
        first = self.applicant('First', 'APPROVED')
        other = self.applicant('Other', 'APPROVED')
        transfer = ApplicantTransferRequest.objects.create(applicant=other, new_brgy=self.brgy, status='APPROVED')
        self.assertEqual(transfer.pk, first.pk)  # same number, different record
        self.assertRedirects(self.delete('transfer', transfer.pk), reverse('admin-applications'), fetch_redirect_response=False)
        self.assertFalse(ApplicantTransferRequest.objects.exists())
        self.assertEqual(Applicant.objects.count(), 2)

    def test_nothing_is_deleted_without_typing_delete(self):
        pending = self.applicant('Pending')
        for typed in ['', 'delete', 'DELET', 'yes']:
            self.delete('new', pending.pk, typed)
        self.assertTrue(Applicant.objects.filter(pk=pending.pk).exists())
        self.assertContains(self.client.get(reverse('admin-applications')), 'Type DELETE to confirm')

    def test_verified_applicant_is_deleted_with_receipts_biometrics_and_files(self):
        verified = self.applicant('Verified', 'APPROVED')
        verified.verification_status = 'VERIFIED'
        verified.save()
        biometric = ApplicantBiometric.objects.create(applicant=verified, completed=True, biometrics_completed=True)
        biometric.left_finger.save('left.png', ContentFile(b'png'), save=True)
        old = BiometricHistory.objects.create(applicant=verified, replaced_by_type='TRANSFER')
        old.right_finger.save('old-right.png', ContentFile(b'png'), save=True)
        AcknowledgmentReceipt.objects.create(applicant=verified, application_number='100000000001', issued_by=self.admin)
        ApplicantTransferRequest.objects.create(applicant=verified, new_brgy=self.brgy, status='APPROVED')
        files = [(f.storage, f.name) for f in (biometric.left_finger, old.right_finger)]
        with self.captureOnCommitCallbacks(execute=True):
            response = self.delete('new', verified.pk)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Applicant.objects.filter(pk=verified.pk).exists())
        self.assertFalse(AcknowledgmentReceipt.objects.exists())
        self.assertFalse(ApplicantBiometric.objects.exists())
        self.assertFalse(BiometricHistory.objects.exists())
        self.assertFalse(ApplicantTransferRequest.objects.exists())
        self.assertTrue(all(not storage.exists(name) for storage, name in files))
        self.assertContains(self.client.get(reverse('admin-applications')), 'was permanently deleted')

    def test_unknown_type_get_and_non_superuser_are_refused(self):
        pending = self.applicant('Safe')
        self.assertEqual(self.delete('unknown', pending.pk).status_code, 404)
        self.assertEqual(self.client.get(reverse('delete-application', args=['new', pending.pk])).status_code, 405)
        staff = get_user_model().objects.create_user(username='staffonly', password='test-password', is_staff=True)
        self.client.force_login(staff)
        self.delete('new', pending.pk)
        self.assertTrue(Applicant.objects.filter(pk=pending.pk).exists())

    def test_list_has_typed_confirmation_dialog_and_typed_links(self):
        applicant = self.applicant('Linked', 'APPROVED')
        transfer = ApplicantTransferRequest.objects.create(applicant=applicant, new_brgy=self.brgy, status='PENDING')
        listing = self.client.get(reverse('admin-applications'))
        self.assertContains(listing, reverse('delete-application', args=['new', applicant.pk]))
        self.assertContains(listing, reverse('delete-application', args=['transfer', transfer.pk]))
        self.assertContains(listing, 'id="deleteApplicationDialog"')
        self.assertContains(listing, 'data-whole-applicant="true"')
        self.assertContains(listing, 'js/delete-application-dialog.js')
        self.assertNotContains(listing, 'Approved applications cannot be deleted')
