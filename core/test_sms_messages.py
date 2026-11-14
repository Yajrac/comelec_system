"""Short applicant SMS texts and the SMS_PROVIDER switch (providers mocked)."""
from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings

from Applicants.models import Applicant
from core.views import send_approval_sms, send_disapproval_sms, sms_text


class SmsMessageTests(TestCase):
    def setUp(self):
        self.applicant = Applicant.objects.create(
            lastname='Peña', firstname='María', middlename='Palacio', age=26, sex='Female',
            birthdate=date(2000, 1, 2), birthplace='X', phone='09171234567',
            office_visit_date=date(2026, 9, 30), office_visit_slot=3)

    @patch('core.views.send_iprog_sms', return_value=True)
    def test_approval_text_has_reference_date_and_plain_letters(self, iprog):
        send_approval_sms(self.applicant, 'Transfer')
        number, message = iprog.call_args.args
        self.assertEqual(number, '09171234567')
        self.assertEqual(message, f'Hi Maria Pena, your Transfer is APPROVED. Ref: {self.applicant.registration_reference}. '
                                  'Visit Pio Duran Registration Office any working day from Sep 28 to Sep 30, 2026 '
                                  'for fingerprints and signature.')
        self.assertTrue(message.isascii())
        self.assertLessEqual(len(message), 306)  # at most two SMS parts

    @patch('core.views.send_iprog_sms', return_value=True)
    def test_disapproval_text_fits_one_sms(self, iprog):
        send_disapproval_sms(self.applicant, 'Reinstatement request')
        message = iprog.call_args.args[1]
        self.assertEqual(message, 'Hi Maria Pena, your Reinstatement request was DISAPPROVED. '
                                  'Please visit the Pio Duran Registration Office for details.')
        self.assertLessEqual(len(message), 160)

    @override_settings(SMS_PROVIDER='semaphore')
    @patch('core.views.send_iprog_sms')
    @patch('core.views.send_semaphore_sms', return_value=True)
    def test_semaphore_is_used_when_selected_and_iprog_is_not(self, semaphore, iprog):
        self.assertTrue(send_disapproval_sms(self.applicant, 'Transfer request'))
        semaphore.assert_called_once()
        iprog.assert_not_called()

    def test_sms_text_removes_accents_and_extra_spaces(self):
        self.assertEqual(sms_text('Niño  “Ñañez”'), 'Nino Nanez')
