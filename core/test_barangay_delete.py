from datetime import date
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from Applicants.models import Applicant, Barangay

@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class BarangayDeleteTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_superuser(username='deleteadmin', password='test-password')
        self.client.force_login(admin)
        self.barangay = Barangay.objects.create(name='Caratagan')

    def test_used_barangay_is_protected_and_address_survives(self):
        applicant = Applicant.objects.create(lastname='Test', firstname='Juan', age=26,
            sex='Male', birthdate=date(2000, 1, 2), birthplace='Pio Duran',
            brgy=self.barangay, phone='09171234567', father='Pedro', mother='Maria')
        with self.assertRaises(ProtectedError):
            self.barangay.delete()
        response = self.client.post(reverse('delete-brgy', args=[self.barangay.pk]), HTTP_ACCEPT='application/json')
        self.assertEqual(response.status_code, 409)
        applicant.refresh_from_db()
        self.assertEqual(applicant.brgy_id, self.barangay.pk)

    def test_unused_barangay_deletes_only_after_post(self):
        url = reverse('delete-brgy', args=[self.barangay.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Barangay.objects.filter(pk=self.barangay.pk).exists())
        response = self.client.post(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json(), {'deleted': True})
        self.assertFalse(Barangay.objects.filter(pk=self.barangay.pk).exists())

    def test_list_has_modal(self):
        self.assertContains(self.client.get(reverse('brgy_list')), 'barangayDeleteDialog')

    def test_non_admin_cannot_delete(self):
        user = get_user_model().objects.create_user(username='ordinary')
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse('delete-brgy', args=[self.barangay.pk])).status_code, 302)
        self.assertTrue(Barangay.objects.filter(pk=self.barangay.pk).exists())
