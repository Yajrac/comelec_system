"""Home page status check by reference number."""
from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from Applicants.models import Applicant, ApplicantTransferRequest, Barangay
from Applicants.status import lookup, normalize_reference


@override_settings(PAGE_RATE_LIMIT_REQUESTS=0, STATUS_LOOKUP_MAX_PER_MINUTE=0,
                   STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                             'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class StatusLookupTests(TestCase):
    def setUp(self):
        cache.clear()
        self.brgy = Barangay.objects.create(name='Agol')
        self.applicant = Applicant.objects.create(
            lastname='Diaz', firstname='Maria Althea', middlename='Palacio', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='Pio Duran', phone='09171234567', email='maria@example.com',
            brgy=self.brgy, status='PENDING')
        self.ref = self.applicant.registration_reference

    def check(self, reference, fragment=False):
        headers = {'HTTP_X_STATUS_FRAGMENT': '1'} if fragment else {}
        return self.client.post('/check-status/', {'reference': reference}, **headers)

    def test_reference_formats_are_accepted(self):
        bare = self.ref.removeprefix('PD-')
        for typed in (self.ref, self.ref.lower(), f'  {bare[:8]} {bare[8:]} ', bare):
            self.assertEqual(normalize_reference(typed), self.ref)
        self.assertEqual(normalize_reference('PD-123'), '')

    def test_page_link_and_result_without_javascript(self):
        home = self.client.get('/')
        self.assertContains(home, 'href="/check-status/"')  # header menu and the hero link
        page = self.client.get('/check-status/')
        self.assertContains(page, 'Registration Reference Number')
        self.assertContains(page, 'PD- followed by your 32-character reference')
        page = self.check(self.ref)
        self.assertContains(page, 'MARIA D.')
        self.assertContains(page, 'Pending review')

    def test_only_short_name_and_statuses_are_shown(self):
        body = self.check(self.ref, fragment=True).content.decode()
        self.assertIn('MARIA D.', body)
        for private in ('Althea', 'Palacio', '09171234567', 'maria@example.com', '2000', 'Agol', 'Pio Duran'):
            self.assertNotIn(private, body)

    def test_not_found_and_invalid(self):
        self.assertContains(self.check('PD-' + '0' * 32, fragment=True), 'No application was found')
        self.assertContains(self.check('hello', fragment=True), 'Enter a valid reference number')

    def test_approved_with_visit_window_then_verified(self):
        self.applicant.status = 'APPROVED'
        self.applicant.verification_status = 'BIOMETRICS_PENDING'
        self.applicant.office_visit_date = date(2026, 11, 19)
        self.applicant.save()
        with patch('core.scheduling.timezone.localdate', return_value=date(2026, 11, 18)):
            result = lookup(self.ref)
        statuses = [row['status'] for row in result['rows']]
        self.assertEqual(statuses, ['Approved', 'Biometrics pending', 'Any working day, Nov 17 to Nov 19, 2026'])
        with patch('core.scheduling.timezone.localdate', return_value=date(2026, 11, 25)):
            self.assertIn('window has passed', lookup(self.ref)['note'])
        self.applicant.verification_status = 'VERIFIED'
        self.applicant.save()
        self.assertEqual(lookup(self.ref)['rows'][-1]['status'], 'Verified - registration complete')

    def test_disapproved_and_suspended(self):
        self.applicant.status, self.applicant.is_active = 'DISAPPROVED', False
        self.applicant.save()
        self.assertIn('Disapproved', lookup(self.ref)['rows'][0]['status'])
        self.applicant.status = 'APPROVED'
        self.applicant.save()
        self.assertEqual(lookup(self.ref)['rows'][0]['status'], 'On hold')

    def test_requests_are_listed_newest_first(self):
        ApplicantTransferRequest.objects.create(applicant=self.applicant, new_brgy=self.brgy, status='PENDING')
        result = lookup(self.ref)
        self.assertEqual(result['requests'][0]['label'], 'Transfer')
        self.assertEqual(result['requests'][0]['status'], 'Pending review')

    @override_settings(STATUS_LOOKUP_MAX_PER_MINUTE=2)
    def test_shared_limit(self):
        self.assertEqual(self.check(self.ref).status_code, 200)
        self.assertEqual(self.check(self.ref).status_code, 200)
        response = self.check(self.ref, fragment=True)
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Too many status checks', status_code=429)
