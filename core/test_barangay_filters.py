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

    def test_admin_tabs_keep_type_filter_only_in_history(self):
        for applicant in self.records:
            ApplicantBiometric.objects.create(applicant=applicant, biometrics_completed=True, completed=True)
        url = reverse('admin-applicants')
        response = self.client.get(url, {'application_type': 'TRANSFER'})
        self.assertEqual(response.context['page_obj'].paginator.count, 3)
        self.assertNotContains(response, 'id="applicationTypeFilter"')
        self.assertNotContains(response, '<th>Latest Application</th>')
        response = self.client.get(url, {'view':'history', 'application_type':'TRANSFER', 'barangay':self.barangay.pk})
        self.assertEqual(response.context['page_obj'].paginator.count, 2)
        self.assertEqual({row['applicant'].pk for row in response.context['history_rows']}, {self.records[0].pk,self.records[1].pk})
        self.assertContains(response, 'value="TRANSFER" selected')
        response = self.client.get(url, {'view':'history','application_type':'TRANSFER','search':'Pending'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        self.assertEqual(response.context['history_rows'][0]['status'], 'PENDING')
        response = self.client.get(url, {'view':'history','application_type':'UPDATE'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_detail_history_retains_all_requests_and_filter_has_no_duplicate_rows(self):
        for applicant in self.records:
            ApplicantBiometric.objects.create(applicant=applicant, biometrics_completed=True, completed=True)
        applicant = self.records[0]
        rejected = ApplicantTransferRequest.objects.create(applicant=applicant, status='DISAPPROVED')
        pending = ApplicantTransferRequest.objects.create(applicant=applicant, status='PENDING')
        from core.application_history import application_history
        history = application_history(applicant)
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0]['reference'], f'TRANSFER-{pending.pk}')
        self.assertEqual({row['status'] for row in history}, {'APPROVED', 'DISAPPROVED', 'PENDING'})
        response = self.client.get(reverse('admin-applicants'), {'application_type':'TRANSFER', 'search':'Transferred'})
        self.assertEqual(response.context['page_obj'].paginator.count, 1)
        history_response = self.client.get(reverse('admin-applicants'), {'view':'history','application_type':'TRANSFER','search':'Transferred'})
        self.assertEqual(history_response.context['page_obj'].paginator.count, 3)
        response = self.client.get(reverse('admin-applicant-detail', args=[applicant.pk]))
        self.assertContains(response, 'Application History')
        self.assertContains(response, f'TRANSFER-{rejected.pk}')
        self.assertEqual(len(response.context['application_history']), 4)
        applicant.refresh_from_db()
        self.assertEqual(applicant.application_type, 'NEW')
