from django.test import SimpleTestCase
from Applicants.application_types import APPLICATION_TYPE_LABELS
from Applicants.models import Applicant, ApplicantUpdateRequest, ApplicantTransferRequest, ApplicantReactivationRequest, ApplicantReinstatementRequest

class ApplicationTypeLabelTests(SimpleTestCase):
    def test_saved_codes_have_official_display_names(self):
        for code, label in APPLICATION_TYPE_LABELS.items():
            record = Applicant(application_type=code)
            self.assertEqual(record.application_type, code)
            self.assertEqual(record.get_application_type_display(), label)
            self.assertEqual(label, label.upper())
        for model, code in [(ApplicantUpdateRequest, 'UPDATE'), (ApplicantTransferRequest, 'TRANSFER'),
                            (ApplicantReactivationRequest, 'REACTIVATION'), (ApplicantReinstatementRequest, 'REINSTATEMENT')]:
            self.assertEqual(model().get_application_type_display(), APPLICATION_TYPE_LABELS[code])
