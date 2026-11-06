from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.utils import timezone


def download_applicant_list(groups, period_label="All months / All years"):
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph

    font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    if "ReportVera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ReportVera", str(font_path)))
    buffer = BytesIO()
    generated = timezone.localtime()
    logo = finders.find("images/PIODURAN.png")
    width, height = A4
    style = ParagraphStyle("record", fontName="ReportVera", fontSize=8, leading=12)
    rows = [["No.", "Applicant's Name", "Applicant's Address"]]
    for group in groups:
        for row in group["rows"]:
            rows.append([str(row["number"]), Paragraph(escape(row["name"]), style),
                         Paragraph(escape(row["address"]), style)])
    if len(rows) == 1:
        rows.append(["", "No applicants to display.", ""])
    table = LongTable(rows, colWidths=[42, 270, width - 384], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "ReportVera"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")),
        ("GRID", (0, 0), (-1, 0), .6, colors.black),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    def decorate(canvas, document):
        canvas.saveState()
        if logo:
            canvas.drawImage(logo, 130, height - 82, width=46, height=46, mask="auto", preserveAspectRatio=True)
        canvas.setFont("ReportVera", 10)
        canvas.drawCentredString(width / 2, height - 48, "Republic of the Philippines")
        canvas.drawCentredString(width / 2, height - 63, "Pio Duran Voter Registration")
        canvas.setFont("ReportVera", 9)
        canvas.drawCentredString(width / 2, height - 98, "PROVINCE: ALBAY")
        canvas.drawCentredString(width / 2, height - 113, "CITY / MUNICIPALITY: PIO DURAN")
        canvas.setFont("ReportVera", 11)
        canvas.drawCentredString(width / 2, height - 140, "LIST OF APPLICANTS")
        canvas.setFont("ReportVera", 8)
        canvas.drawCentredString(width / 2, height - 153, period_label)
        canvas.setFont("ReportVera", 7)
        canvas.drawString(36, 51, "Application records only. This is not a certified list of registered voters.")
        canvas.drawString(36, 40, "Contains personal information. For authorized registration processing only.")
        canvas.drawString(36, 25, f"Generated: {generated:%b %d, %Y %I:%M %p}")
        canvas.drawRightString(width - 36, 25, f"Page {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36,
        topMargin=174, bottomMargin=68, title="Applicant Registration Report", author="Pio Duran Registration System")
    document.build([table], onFirstPage=decorate, onLaterPages=decorate)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="applicant-list-{generated:%Y%m%d}.pdf"'
    return response


def download_summary(title, records, columns, period_label, note=""):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, LongTable, TableStyle, Paragraph
    # Register the same Unicode font used by the applicant report.
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "ReportVera" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("ReportVera", str(Path(reportlab.__file__).parent / "fonts" / "Vera.ttf")))
    buffer = BytesIO()
    width, height = landscape(A4)
    style = ParagraphStyle("summary", fontName="ReportVera", fontSize=8, leading=12)
    rows = [[Paragraph(escape(label), style) for key, label in columns]]
    rows += [[Paragraph(escape(str(record.get(key, ""))), style) for key, label in columns] for record in records]
    table = LongTable(rows, colWidths=[(width - 72) * .3] + [(width - 72) * .7 / (len(columns) - 1)] * (len(columns) - 1), repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e6e6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 0), (-1, 0), .5, colors.black)]))
    generated = timezone.localtime()
    logo = finders.find("images/PIODURAN.png")

    def decorate(canvas, doc):
        canvas.saveState()
        if logo:
            canvas.drawImage(logo, width / 2 - 190, height - 88, width=50, height=50,
                             mask="auto", preserveAspectRatio=True)
        canvas.setFont("ReportVera", 10)
        canvas.drawCentredString(width / 2, height - 48, "Republic of the Philippines")
        canvas.drawCentredString(width / 2, height - 63, "Pio Duran Voter Registration")
        canvas.setFont("ReportVera", 9)
        canvas.drawCentredString(width / 2, height - 81, "Pio Duran, Albay")
        canvas.setFont("ReportVera", 12)
        canvas.drawCentredString(width / 2, height - 110, title.upper())
        canvas.setFont("ReportVera", 9)
        canvas.drawCentredString(width / 2, height - 128, period_label)
        if note:
            paragraph = Paragraph(escape(note), style)
            _, note_height = paragraph.wrap(width - 72, 40)
            paragraph.drawOn(canvas, 36, height - 140 - note_height)
        canvas.setFont("ReportVera", 8)
        canvas.drawString(36, 24, f"Generated: {generated:%b %d, %Y %I:%M %p}")
        canvas.drawRightString(width - 36, 24, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=36, rightMargin=36,
        topMargin=178, bottomMargin=48, title=title)
    doc.build([table], onFirstPage=decorate, onLaterPages=decorate)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    filename = title.lower().replace(" ", "-")
    response["Content-Disposition"] = f'attachment; filename="{filename}-{generated:%Y%m%d}.pdf"'
    return response
