"""Shared rendering for saved acknowledgment receipts."""
from io import BytesIO
from xml.sax.saxutils import escape
from django.http import HttpResponse
from django.shortcuts import render

FIELDS = (("lastname", "Last name", ""), ("firstname", "First name", ""), ("middlename", "Middle name", ""), ("application_no", "Application number", ""), ("receipt_date", "Receipt date", ""), ("officer", "Election Officer / Interviewer", ""))

def render_receipt(request, values, application_type):
    if request.GET.get("format") == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=(297*mm, 148*mm), rightMargin=15*mm, leftMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm)
        styles = getSampleStyleSheet()
        text = lambda value: Paragraph(escape(value or "________________________"), styles["Normal"])
        story = [Paragraph("ACKNOWLEDGMENT RECEIPT", styles["Title"]), text("Commission on Elections - Pio Duran, Albay"), Spacer(1, 7*mm)]
        rows = [[text("Type of Application"), text(application_type), text("Application No."), text(values["application_no"])]]
        for key, label, default in FIELDS:
            if key != "application_no":
                rows.append([text(label), text(values[key]), "", ""])
        table = Table(rows, colWidths=[48*mm, 83*mm, 40*mm, 86*mm])
        table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("LINEBELOW", (0,0), (-1,0), 0.5, colors.HexColor("#d5dce5"))]))
        story += [table, Spacer(1, 4*mm), text("This is to acknowledge receipt of your application. Your application is subject to Approval/Disapproval by the Election Registration Board (ERB). You need not appear in the ERB hearing unless required through a written notice."), Spacer(1, 7*mm), text("EO / Interviewer signature above printed name: ______________________________")]
        document.build(story)
        response = HttpResponse(output.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="acknowledgment-receipt.pdf"'
        response["Cache-Control"] = "no-store"
        return response
    fields = [{"key": key, "label": label, "value": values[key], "type": "date" if key.endswith("date") else "text"} for key, label, default in FIELDS]
    return render(request, "comelec/applications/acknowledgment_receipt.html", {"fields": fields, "application_types": (application_type,), "application_type": application_type})
