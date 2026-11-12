"""Deleting from the Applications list removes only the clicked record."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from Applicants.models import (AcknowledgmentReceipt, Applicant, ApplicantTransferRequest, Barangay)


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

    def delete(self, kind, pk):
        return self.client.post(reverse('delete-application', args=[kind, pk]))

    def test_deleting_a_request_never_deletes_the_applicant_with_the_same_id(self):
        first = self.applicant('First', 'APPROVED')
        other = self.applicant('Other', 'APPROVED')
        transfer = ApplicantTransferRequest.objects.create(applicant=other, new_brgy=self.brgy, status='PENDING')
        self.assertEqual(transfer.pk, first.pk)  # same number, different record
        self.assertRedirects(self.delete('transfer', transfer.pk), reverse('admin-applications'), fetch_redirect_response=False)
        self.assertFalse(ApplicantTransferRequest.objects.exists())
        self.assertEqual(Applicant.objects.count(), 2)

    def test_pending_new_registration_can_be_deleted(self):
        pending = self.applicant('Pending')
        self.delete('new', pending.pk)
        self.assertFalse(Applicant.objects.filter(pk=pending.pk).exists())
        self.assertContains(self.client.get(reverse('admin-applications')), 'was deleted')

    def test_approved_records_are_kept_with_a_message(self):
        approved = self.applicant('Approved', 'APPROVED')
        AcknowledgmentReceipt.objects.create(applicant=approved, application_number='100000000001', issued_by=self.admin)
        transfer = ApplicantTransferRequest.objects.create(applicant=approved, new_brgy=self.brgy, status='APPROVED')
        self.delete('new', approved.pk)
        self.delete('transfer', transfer.pk)
        self.assertTrue(Applicant.objects.filter(pk=approved.pk).exists())
        self.assertTrue(ApplicantTransferRequest.objects.filter(pk=transfer.pk).exists())
        listing = self.client.get(reverse('admin-applications'))
        self.assertContains(listing, 'cannot be deleted')
        self.assertContains(listing, 'Approved applications cannot be deleted')

    def test_protected_record_shows_message_instead_of_server_error(self):
        pending = self.applicant('Protected')
        AcknowledgmentReceipt.objects.create(applicant=pending, application_number='100000000002', issued_by=self.admin)
        response = self.delete('new', pending.pk)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Applicant.objects.filter(pk=pending.pk).exists())

    def test_unknown_type_get_and_non_superuser_are_refused(self):
        pending = self.applicant('Safe')
        self.assertEqual(self.delete('unknown', pending.pk).status_code, 404)
        self.assertEqual(self.client.get(reverse('delete-application', args=['new', pending.pk])).status_code, 405)
        staff = get_user_model().objects.create_user(username='staffonly', password='test-password', is_staff=True)
        self.client.force_login(staff)
        self.delete('new', pending.pk)
        self.assertTrue(Applicant.objects.filter(pk=pending.pk).exists())

    def test_list_links_include_the_application_type(self):
        applicant = self.applicant('Linked')
        transfer = ApplicantTransferRequest.objects.create(applicant=applicant, new_brgy=self.brgy, status='PENDING')
        listing = self.client.get(reverse('admin-applications'))
        self.assertContains(listing, reverse('delete-application', args=['new', applicant.pk]))
        self.assertContains(listing, reverse('delete-application', args=['transfer', transfer.pk]))
