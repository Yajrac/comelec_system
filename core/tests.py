from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, override_settings

from core.views import send_semaphore_sms


@override_settings(SEMAPHORE_API_KEY="fake-key", SEMAPHORE_SENDER_NAME="Approved")
class SemaphoreSMSTests(SimpleTestCase):
    @patch("core.views.requests.post")
    def test_normalizes_numbers_and_submits_form_fields(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = [{"message_id": 12, "status": "Queued"}]
        for number in ("09171234567", "+639171234567", "9171234567", "639171234567"):
            with self.subTest(number=number):
                self.assertTrue(send_semaphore_sms(number, "Registration update"))
                post.assert_called_with(
                    "https://api.semaphore.co/api/v4/messages",
                    data={"apikey": "fake-key", "number": "639171234567",
                          "message": "Registration update", "sendername": "Approved"},
                    timeout=15,
                )

    @patch("core.views.requests.post")
    def test_rejects_invalid_recipients_without_network(self, post):
        for number in (None, "", "639abcdefghij", "09171234567,09181234567", "123"):
            self.assertFalse(send_semaphore_sms(number, "Update"))
        post.assert_not_called()

    @override_settings(SEMAPHORE_API_KEY="")
    @patch("core.views.requests.post")
    def test_missing_credentials_does_not_send(self, post):
        self.assertFalse(send_semaphore_sms("09171234567", "Update"))
        post.assert_not_called()

    @override_settings(SEMAPHORE_SENDER_NAME="")
    @patch("core.views.requests.post")
    def test_uses_account_default_sender(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = [{"message_id": 12, "status": "Pending"}]
        self.assertTrue(send_semaphore_sms("09171234567", "Update"))
        self.assertNotIn("sendername", post.call_args.kwargs["data"])

    @patch("core.views.requests.post")
    def test_rejects_api_failures(self, post):
        for code, result in [(429, {}), (401, {}), (200, {}), (200, []),
                             (200, [{"message_id": 1, "status": "Failed"}]),
                             (200, [{"status": "Queued"}])]:
            with self.subTest(code=code, result=result):
                post.return_value = Mock(status_code=code)
                post.return_value.json.return_value = result
                self.assertFalse(send_semaphore_sms("09171234567", "Update"))

    @patch("core.views.requests.post")
    def test_timeout_and_invalid_json_fail_without_retry(self, post):
        post.side_effect = requests.Timeout()
        self.assertFalse(send_semaphore_sms("09171234567", "Update"))
        post.assert_called_once()
        post.reset_mock()
        post.side_effect = None
        post.return_value = Mock(status_code=200)
        post.return_value.json.side_effect = ValueError()
        self.assertFalse(send_semaphore_sms("09171234567", "Update"))
        post.assert_called_once()


class BarangayCatalogTests(SimpleTestCase):
    def test_catalog_and_canonical_names(self):
        from core.barangays import PIO_DURAN_BARANGAYS, canonical_barangay_name
        self.assertEqual(len(PIO_DURAN_BARANGAYS), 33)
        self.assertEqual(len(set(PIO_DURAN_BARANGAYS)), 33)
        self.assertEqual(canonical_barangay_name("  basicao   coastal "), "Basicao Coastal")
        self.assertIsNone(canonical_barangay_name("Other Municipality"))

    @patch("core.views.render")
    @patch("core.views.Barangay.objects.get_or_create")
    @patch("core.views.Barangay.objects.values_list", return_value=["Agol"])
    def test_rejects_unknown_and_duplicate_names(self, names, create, render):
        from django.test import RequestFactory
        from types import SimpleNamespace
        from core.views import add_brgy
        for name in ["", "Not a Pio Duran Barangay", " agol "]:
            request = RequestFactory().post("/comelec/add-barangay/", {"name": name})
            request.user = SimpleNamespace(is_authenticated=True)
            add_brgy(request)
            self.assertIn("error", render.call_args.args[2])
            self.assertNotIn("Agol", render.call_args.args[2]["available_barangays"])
        create.assert_not_called()

    @patch("core.views.Barangay.objects.get_or_create", return_value=(Mock(), True))
    @patch("core.views.Barangay.objects.values_list", return_value=[])
    def test_saves_only_canonical_name(self, names, create):
        from django.test import RequestFactory
        from types import SimpleNamespace
        from core.views import add_brgy
        request = RequestFactory().post("/comelec/add-barangay/", {"name": " basicao   coastal "})
        request.user = SimpleNamespace(is_authenticated=True)
        self.assertEqual(add_brgy(request).status_code, 302)
        create.assert_called_once_with(name="Basicao Coastal")


@override_settings(IPROG_SMS_API_TOKEN="fake-token")
class IProgSMSTests(SimpleTestCase):
    @patch("core.views.requests.post")
    def test_queues_normalized_numbers(self, post):
        from core.views import send_iprog_sms
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"status": 200, "message_id": "test-message"}
        for number in ["09171234567", "+639171234567", "639171234567", "9171234567"]:
            self.assertTrue(send_iprog_sms(number, "Application update"))
            post.assert_called_with("https://www.iprogsms.com/api/v1/sms_messages",
                json={"api_token": "fake-token", "phone_number": "639171234567", "message": "Application update"}, timeout=15)

    @override_settings(IPROG_SMS_API_TOKEN="")
    @patch("core.views.requests.post")
    def test_missing_token_does_not_send(self, post):
        from core.views import send_iprog_sms
        self.assertFalse(send_iprog_sms("09171234567", "Update"))
        post.assert_not_called()

    @patch("core.views.requests.post")
    def test_invalid_input_does_not_send(self, post):
        from core.views import send_iprog_sms
        for number, message in [("123", "Update"), (None, "Update"), ("09171234567", "")]:
            self.assertFalse(send_iprog_sms(number, message))
        post.assert_not_called()

    @patch("core.views.requests.post")
    def test_rejections_and_network_failure_do_not_retry(self, post):
        import requests
        from core.views import send_iprog_sms
        post.return_value.status_code = 200
        for payload in [{"status": 500}, [], {"status": 200}]:
            post.reset_mock()
            post.return_value.json.return_value = payload
            self.assertFalse(send_iprog_sms("09171234567", "Update"))
            self.assertEqual(post.call_count, 1)
        post.reset_mock()
        post.side_effect = requests.Timeout()
        self.assertFalse(send_iprog_sms("09171234567", "Update"))
        self.assertEqual(post.call_count, 1)
