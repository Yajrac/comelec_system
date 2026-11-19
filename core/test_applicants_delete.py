"""Applicants pages: Delete (typed DELETE) instead of Suspend, and the Municipal Report name."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from Applicants.models import Applicant, ApplicantBiometric, ApplicantTransferRequest, Barangay


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ApplicantDeleteTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='deleteadmin', password='x'))
        self.brgy = Barangay.objects.create(name='Agol')
        self.applicant = Applicant.objects.create(
            lastname='Reyes', firstname='Ana', age=26, sex='Female', birthdate=date(2000, 1, 2),
            birthplace='Pio Duran', phone='09171234567', brgy=self.brgy, status='APPROVED',
            verification_status='VERIFIED')
        ApplicantBiometric.objects.create(applicant=self.applicant, biometrics_completed=True, completed=True)
        self.transfer = ApplicantTransferRequest.objects.create(
            applicant=self.applicant, current_brgy=self.brgy, new_brgy=self.brgy, status='APPROVED')
        self.list_url = reverse('admin-applicants')

    def test_suspend_is_gone(self):
        with self.assertRaises(NoReverseMatch):
            reverse('admin-suspend-applicant', args=[self.applicant.pk])
        for url in (self.list_url, reverse('admin-applicant-detail', args=[self.applicant.pk])):
            response = self.client.get(url)
            self.assertNotContains(response, 'Suspend')
            self.assertContains(response, 'id="deleteApplicationDialog"')

    def test_rows_and_detail_page_offer_delete(self):
        response = self.client.get(self.list_url)
        self.assertContains(response, reverse('delete-application', args=['new', self.applicant.pk]))
        self.assertContains(response, reverse('delete-application', args=['transfer', self.transfer.pk]))
        response = self.client.get(reverse('admin-applicant-detail', args=[self.applicant.pk]))
        self.assertContains(response, 'Delete Applicant')

    def test_delete_request_returns_to_the_applicants_page(self):
        back = self.list_url + '?barangay=' + str(self.brgy.pk)
        response = self.client.post(reverse('delete-application', args=['transfer', self.transfer.pk]),
                                    {'confirm_text': 'DELETE', 'next': back})
        self.assertRedirects(response, back, fetch_redirect_response=False)
        self.assertFalse(ApplicantTransferRequest.objects.exists())
        self.assertTrue(Applicant.objects.exists())

    def test_wrong_word_keeps_the_record(self):
        response = self.client.post(reverse('delete-application', args=['new', self.applicant.pk]),
                                    {'confirm_text': 'delete', 'next': self.list_url})
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        self.assertTrue(Applicant.objects.exists())

    def test_delete_applicant_from_detail_page(self):
        response = self.client.post(reverse('delete-application', args=['new', self.applicant.pk]),
                                    {'confirm_text': 'DELETE', 'next': self.list_url})
        self.assertRedirects(response, self.list_url, fetch_redirect_response=False)
        self.assertFalse(Applicant.objects.exists())

    def test_other_sites_are_not_followed(self):
        response = self.client.post(reverse('delete-application', args=['transfer', self.transfer.pk]),
                                    {'confirm_text': 'DELETE', 'next': 'https://evil.example/'})
        self.assertRedirects(response, reverse('admin-applications'), fetch_redirect_response=False)

    def test_municipal_report(self):
        response = self.client.get(reverse('admin-reports'))
        self.assertContains(response, 'Municipal Report')
        self.assertNotContains(response, 'Barangay Report')
        response = self.client.get(reverse('admin-reports'), {'format': 'pdf', 'table': 'barangays'})
        self.assertIn('municipal-report-', response['Content-Disposition'])
