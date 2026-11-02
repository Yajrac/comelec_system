from datetime import date
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from Applicants.models import Applicant, Barangay, ApplicantTransferRequest, ApplicantBiometric

@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class BarangayTypeFilterTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='typeadmin', password='test-password'))
        self.barangay = Barangay.objects.create(name='Agol')
        other = Barangay.objects.create(name='Caratagan')
        self.records = []
        for name, barangay, verification in [('Transferred', self.barangay, 'VERIFIED'), ('Pending', self.barangay, 'VERIFIED'), ('Other', other, 'VERIFIED'), ('Unverified', self.barangay, 'UNVERIFIED')]:
            self.records.append(Applicant.objects.create(lastname=name, firstname='Juan', age=26, sex='Male',
                birthdate=date(2000, 1, 2), birthplace='Pio Duran', phone='09171234567',
                brgy=barangay, status='APPROVED', verification_status=verification, is_active=True))
        for applicant in self.records:
            ApplicantTransferRequest.objects.create(applicant=applicant, current_brgy=other,
                new_brgy=applicant.brgy, status='PENDING' if applicant.lastname=='Pending' else 'APPROVED')
        self.url = reverse('barangay_applicants', args=[self.barangay.pk])

    def test_filter_uses_approved_history_and_keeps_barangay_scope(self):
        response = self.client.get(self.url, {'application_type': 'TRANSFER'})
        self.assertEqual(list(response.context['applicants']), [self.records[0]])
        self.assertContains(response, 'aria-current="page"')
        self.assertEqual(response.context['total_verified'], 2)
        counts = {tab['code']: tab['count'] for tab in response.context['application_type_tabs']}
        self.assertEqual(counts['TRANSFER'], 1)
        self.assertEqual(counts[''], 2)

    def test_all_invalid_and_empty_filters(self):
        for code in ['', 'unknown']:
            response = self.client.get(self.url, {'application_type': code})
            self.assertEqual(response.context['applicants'].count(), 2)
        response = self.client.get(self.url, {'application_type': 'UPDATE'})
        self.assertEqual(response.context['applicants'].count(), 0)
        self.assertContains(response, 'No Matching Verified Applicants')

    def test_admin_applicants_type_filter_combines_history_search_and_barangay(self):
        for applicant in self.records:
            ApplicantBiometric.objects.create(applicant=applicant, biometrics_completed=True, completed=True)
        url = reverse('admin-applicants')
        response = self.client.get(url, {'application_type': 'TRANSFER', 'barangay': self.barangay.pk})
        self.assertEqual(list(response.context['applicants']), [self.records[0]])
        self.assertContains(response, 'value="TRANSFER" selected')
        response = self.client.get(url, {'application_type': 'TRANSFER', 'search': 'Pending'})
        self.assertEqual(list(response.context['applicants']), [])
        response = self.client.get(url, {'application_type': 'UPDATE'})
        self.assertEqual(list(response.context['applicants']), [])
        response = self.client.get(url, {'application_type': 'unknown'})
        self.assertEqual(response.context['page_obj'].paginator.count, 3)
