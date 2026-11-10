"""Compact acknowledgment receipt shared by print preview and PDF."""
from io import BytesIO
from xml.sax.saxutils import escape
from django.http import HttpResponse
from django.shortcuts import render

OPTIONS = [('NEW', 'Registration'), ('TRANSFER', 'Transfer'), ('REACTIVATION', 'Reactivation'), ('TRANSFER_REACTIVATION', 'Transfer with Reactivation'), ('UPDATE', 'Change of Name/Correction of Entry'), ('REINSTATEMENT', 'Reinstatement/Inclusion')]
NOTICE = 'This is to acknowledge receipt of your application. Your application is subject to Approval/Disapproval by the Election Registration Board (ERB). You need not appear in the ERB hearing unless required through a written notice.'

def selected_type(label):
    label = label.upper()
    if 'TRANSFER' in label and 'REACTIVATION' in label:
        return 'TRANSFER_REACTIVATION'
    for keyword, code in [('TRANSFER','TRANSFER'), ('REACTIVATION','REACTIVATION'), ('CORRECTION','UPDATE'), ('CHANGE OF NAME','UPDATE'), ('REINSTATEMENT','REINSTATEMENT'), ('INCLUSION','REINSTATEMENT')]:
        if keyword in label:
            return code
    return 'NEW'

def render_receipt(request, values, application_type, applicant_id=None):
    selected = selected_type(application_type)
    names = [{'label': label, 'letters': list(str(values.get(key, '') or '').upper().ljust(28))} for key, label in [('lastname','Last'), ('firstname','First'), ('middlename','Middle')]]
    options = [{'label': label, 'selected': code == selected} for code, label in OPTIONS]
    if request.GET.get('format') == 'pdf':
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Paragraph
        output = BytesIO()
        width, height = 297*mm, 85*mm
        pdf = canvas.Canvas(output, pagesize=(width, height))
        pdf.setTitle('Acknowledgment Receipt')
        left, bottom, right, top = 8*mm, 7*mm, width-8*mm, height-7*mm
        pdf.setLineWidth(.8); pdf.rect(left, bottom, right-left, top-bottom)
        pdf.setFont('Helvetica-Bold', 11); pdf.drawCentredString(width/2, top-6*mm, 'ACKNOWLEDGMENT RECEIPT')
        pdf.setFont('Helvetica', 7); pdf.drawCentredString(width/2, top-10*mm, 'Pio Duran Voter Registration')
        split = 211*mm
        pdf.setFont('Helvetica-Bold', 9); pdf.drawString(left+3*mm, top-16*mm, 'Type of Application')
        for i, option in enumerate(options):
            column, row = (0,i) if i<3 else (1,i-3)
            x,y = left+5*mm+column*66*mm, top-(23+row*6)*mm
            pdf.circle(x,y+1,1.6*mm)
            if option['selected']:
                pdf.line(x-2,y+1,x,y-1); pdf.line(x,y-1,x+4,y+4)
            pdf.setFont('Helvetica',8); pdf.drawString(x+3*mm,y-1,option['label'])
        pdf.setFont('Helvetica',8); pdf.drawRightString(split-5*mm,top-39*mm,'Date: '+str(values.get('receipt_date','')))
        pdf.setFont('Helvetica-Bold',9); pdf.drawString(left+3*mm,top-43*mm,'Application for Registration')
        grid_x,grid_right = left+16*mm,split-5*mm
        for i,name in enumerate(names):
            y=top-(51+i*7)*mm
            pdf.setFont('Helvetica',8); pdf.drawString(left+3*mm,y+2*mm,name['label'])
            cell=(grid_right-grid_x)/len(name['letters'])
            pdf.setFont('Helvetica',min(10,cell*.8))
            for j,letter in enumerate(name['letters']):
                pdf.setStrokeColor(colors.HexColor('#999999'));pdf.setLineWidth(.3)
                pdf.rect(grid_x+j*cell,y,cell,6.5*mm)
                pdf.drawCentredString(grid_x+(j+.5)*cell,y+2*mm,letter)
        x,inner_right=split+2*mm,right-3*mm
        pdf.setStrokeColor(colors.black);pdf.setLineWidth(.5)
        pdf.setFont('Helvetica-Bold',9);pdf.drawCentredString((x+inner_right)/2,top-16*mm,'Application No.')
        number=str(values.get('application_no',''));cell=(inner_right-x)/max(12,len(number))
        for i,digit in enumerate(number):
            pdf.rect(x+i*cell,top-24*mm,cell,6*mm)
            pdf.setFont('Helvetica',10);pdf.drawCentredString(x+(i+.5)*cell,top-22*mm,digit)
        paragraph=Paragraph(escape(NOTICE),ParagraphStyle('receipt',fontName='Helvetica',fontSize=8,leading=11))
        _,ph=paragraph.wrap(inner_right-x,40*mm);paragraph.drawOn(pdf,x,top-27*mm-ph)
        pdf.setFont('Helvetica',8);pdf.drawString(x,bottom+16*mm,'Date of ERB Hearing: ______________')
        officer=Paragraph(escape(str(values.get('officer','') or '')),ParagraphStyle('officer',fontName='Helvetica-Bold',fontSize=8,alignment=1))
        officer.wrap(inner_right-x,12*mm);officer.drawOn(pdf,x,bottom+7*mm)
        pdf.line(x,bottom+6*mm,inner_right,bottom+6*mm)
        pdf.setFont('Helvetica',6.5);pdf.drawCentredString((x+inner_right)/2,bottom+2.5*mm,'EO / Interviewer Signature above Printed Name')
        pdf.showPage();pdf.save()
        response=HttpResponse(output.getvalue(),content_type='application/pdf')
        response['Content-Disposition']='attachment; filename="acknowledgment-receipt.pdf"'
        response['Cache-Control']='no-store'
        return response
    return render(request,'comelec/applications/acknowledgment_receipt.html',{'receipt_values':values,'name_rows':names,'application_options':options,'number_digits':list(str(values['application_no'])),'receipt_notice':NOTICE,'receipt_applicant_id':applicant_id})
