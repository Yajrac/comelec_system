"""SK Registration: a New Registration of someone 15-17 on election day (computed from the birthdate)."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from Applicants.eligibility import is_sk, sk_filter
from Applicants.models import Applicant, ApplicantBiometric, Barangay
from Applicants.status import registration_status

ELECTION = "2028-05-08"
PAGES = dict(VOTER_ELECTION_DATE=ELECTION, PAGE_RATE_LIMIT_REQUESTS=0,
             STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
                       'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})


@override_settings(VOTER_ELECTION_DATE=ELECTION)
class SkRuleTests(SimpleTestCase):
    def test_age_on_election_day(self):
        self.assertTrue(is_sk(date(2013, 5, 8)))       # turns 15 on election day
        self.assertFalse(is_sk(date(2013, 5, 9)))      # still 14
        self.assertTrue(is_sk(date(2010, 5, 9)))       # 17, turns 18 the day after
        self.assertFalse(is_sk(date(2010, 5, 8)))      # turns 18 on election day: regular
        self.assertFalse(is_sk(date(1990, 1, 1)))
        self.assertFalse(is_sk(None))


@override_settings(**PAGES)
class SkPagesTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='skadmin', password='x'))
        self.brgy = Barangay.objects.create(name='Agol')
        self.sk = self.make('Youth', date(2012, 1, 10))
        self.regular = self.make('Adult', date(1999, 1, 10))

    def make(self, lastname, born):
        applicant = Applicant.objects.create(
            lastname=lastname, firstname='Ana', age=16, sex='Female', birthdate=born, birthplace='Pio Duran',
            phone='09171234567', brgy=self.brgy, status='APPROVED', verification_status='VERIFIED')
        ApplicantBiometric.objects.create(applicant=applicant, biometrics_completed=True, completed=True)
        return applicant

    def test_database_filter_matches_the_rule(self):
        for born in (date(2013, 5, 8), date(2013, 5, 9), date(2010, 5, 9), date(2010, 5, 8), date(2012, 2, 29)):
            Applicant.objects.filter(pk=self.sk.pk).update(birthdate=born)
            self.assertEqual(Applicant.objects.filter(sk_filter(), pk=self.sk.pk).exists(), is_sk(born), born)

    def test_applications_page_badge_and_filter(self):
        url = reverse('admin-applications')
        response = self.client.get(url)
        self.assertContains(response, 'APPLICATION FOR SK REGISTRATION')
        self.assertContains(response, 'application-sk')
        self.assertContains(response, '<option\n                                        value="SK"', html=False)
        names = lambda r: {a['applicant_name'] for a in r.context['page_obj']}
        self.assertEqual(names(self.client.get(url, {'application_type': 'SK'})), {str(self.sk)})
        self.assertEqual(names(self.client.get(url, {'application_type': 'NEW'})), {str(self.regular)})

    def test_applicants_page_label_and_filter(self):
        url = reverse('admin-applicants')
        response = self.client.get(url, {'application_type': 'SK'})
        rows = list(response.context['history_rows'])
        self.assertEqual([row['applicant'] for row in rows], [self.sk])
        self.assertEqual(rows[0]['label'], 'SK Registration')
        rows = list(self.client.get(url, {'application_type': 'NEW'}).context['history_rows'])
        self.assertEqual([row['applicant'] for row in rows], [self.regular])

    def test_detail_page(self):
        response = self.client.get(reverse('admin-application-new-detail', args=[self.sk.pk]))
        self.assertContains(response, 'SK REGISTRATION')

    def test_reports(self):
        response = self.client.get(reverse('admin-reports'))
        rows = {row['code']: row for row in response.context['application_type_report']}
        self.assertEqual((rows['NEW']['total'], rows['SK']['total']), (1, 1))
        self.assertEqual(rows['SK']['approved'], 1)
        agol = next(row for row in response.context['barangay_report'] if row['name'] == 'Agol')
        self.assertEqual((agol['new'], agol['sk'], agol['total']), (1, 1, 2))
        self.assertContains(response, '<th class="text-center">SK</th>', html=False)

    def test_check_status_uses_the_sk_label(self):
        self.assertEqual(registration_status(self.sk)[0][0][0], 'SK Registration')
        self.assertEqual(registration_status(self.regular)[0][0][0], 'New Registration')

    def test_form_has_the_review_row(self):
        self.client.logout()
        html = self.client.get('/new-registration/').content.decode()
        self.assertIn('id="review_application_type"', html)
        self.assertIn('id="applicationTypeBadge"', html)


@override_settings(**PAGES)
class SkDashboardTests(TestCase):
    def test_dashboard_card_counts_sk_and_links_to_the_filter(self):
        self.client.force_login(get_user_model().objects.create_superuser(username='skdash', password='x'))
        brgy = Barangay.objects.create(name='Agol')
        for born in (date(2012, 1, 10), date(2011, 6, 1), date(1999, 1, 10)):
            Applicant.objects.create(lastname='X', firstname='Y', age=16, sex='Male', birthdate=born,
                                     birthplace='Z', phone='09171234567', brgy=brgy)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['sk_registrations'], 2)
        self.assertContains(response, 'SK Registrations')
        self.assertContains(response, '?application_type=SK')
