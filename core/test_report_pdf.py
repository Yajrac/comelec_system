from unittest.mock import patch
from django.test import SimpleTestCase
from reportlab.pdfgen.canvas import Canvas
from core.report_pdf import download_summary


class SummaryLogoTests(SimpleTestCase):
    def test_logo_is_embedded_and_repeated_on_each_page(self):
        original = Canvas.drawImage
        pages = []
        def draw(canvas, *args, **kwargs):
            pages.append(canvas.getPageNumber())
            return original(canvas, *args, **kwargs)
        rows = [{"name": "Barangay " + str(index), "total": index} for index in range(100)]
        with patch.object(Canvas, "drawImage", autospec=True, side_effect=draw):
            response = download_summary("Barangay Report", rows, [("name", "Barangay"), ("total", "Total")], "All years")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(b"/Subtype /Image", response.content)
        self.assertGreater(len(pages), 1)
        self.assertEqual(pages, list(range(1, len(pages) + 1)))
