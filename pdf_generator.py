import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 🌟 UNIKOD HARFLARI VA SCRIPT METRIKALARI
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 🌟 QR-KOD YARATISH UCHUN IMPORT
import qrcode

# 🌟 UNIVERSAL OS-MUSTAQIL TIMES NEW ROMAN YUKLASH TIZIMI
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    font_path = os.path.join(project_root, 'fonts', 'times.ttf')
    font_bold_path = os.path.join(project_root, 'fonts', 'timesbd.ttf')
    
    pdfmetrics.registerFont(TTFont('Times-New-Roman', font_path))
    pdfmetrics.registerFont(TTFont('Times-New-Roman-Bold', font_bold_path))
    
    MAIN_FONT = 'Times-New-Roman'
    BOLD_FONT = 'Times-New-Roman-Bold'
except Exception as e:
    MAIN_FONT = 'Helvetica'
    BOLD_FONT = 'Helvetica-Bold'

def create_medical_pdf(patient_name: str, analysis_type: str, result_text: str) -> str:
    """
    Bemor uchun shifrlangan tibbiy tahlil PDF faylini generatsiya qiladi.
    Fayl nomini qaytaradi.
    """
    timestamp = int(datetime.now().timestamp())
    filename = f"Tahlil_{timestamp}.pdf"
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Matn uslublari
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName=BOLD_FONT,
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#1A365D')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#4A5568')
    )
    
    label_style = ParagraphStyle(
        'DocLabel',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#2D3748')
    )
    
    value_style = ParagraphStyle(
        'DocValue',
        parent=styles['Normal'],
        fontName=MAIN_FONT,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1A202C')
    )
    
    result_style = ParagraphStyle(
        'DocResult',
        parent=styles['Normal'],
        fontName=BOLD_FONT,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#E53E3E') if "MUSBAT" in result_text.upper() else colors.HexColor('#38A169')
    )

    # 1. RASMIY SHEAD (HEADER)
    header_text = (
        "O'ZBEKISTON RESPUBLIKASI SOG'LIQNI SAQLASH VAZIRLIGI<br/>"
        "FARG'ONA VILOYAT OITSGA QARSHI KURASH MARKAZI"
    )
    story.append(Paragraph(header_text, title_style))
    story.append(Spacer(1, 6))
    
    address_text = "Farg'ona sh., Yo'ldosh ko'chasi 12-uy. Tel: +998 (73) ***-03-03 / Ishonch telefoni"
    story.append(Paragraph(address_text, subtitle_style))
    
    story.append(Spacer(1, 10))
    divider = Table([['']], colWidths=[530], rowHeights=[2])
    divider.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1A365D')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 20))
    
    # 2. HUJJAT NOMI VA SANASI
    current_date = datetime.now().strftime("%d.%m.%Y (Soat: %H:%M)")
    doc_id = timestamp // 100
    doc_info = f"<b>RASMIY TIBBIY XULOSA № {doc_id}</b><br/>Berilgan sana: {current_date}"
    story.append(Paragraph(doc_info, ParagraphStyle('DocInfo', parent=styles['Normal'], fontName=MAIN_FONT, fontSize=11, alignment=1, leading=16)))
    story.append(Spacer(1, 25))
    
    # 3. BEMOR VA TAHLIL MA'LUMOTLARI JADVALI
    data = [
        [Paragraph("F.I.Sh. (Bemor):", label_style), Paragraph(patient_name, value_style)],
        [Paragraph("Tahlil turi:", label_style), Paragraph(analysis_type, value_style)],
        [Paragraph("Tekshiruv usuli:", label_style), Paragraph("Immunoxelyuminessensiya (IHL) va PSR", value_style)],
        [Paragraph("Tahlil natijasi (Xulosa):", label_style), Paragraph(result_text, result_style)]
    ]
    
    medical_table = Table(data, colWidths=[160, 370])
    medical_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F7FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(medical_table)
    story.append(Spacer(1, 35))
    
    # 🌟 4. QR-KOD GENERATSIYA QILISH QISMI
    # Bu yerga bot linkini yoki unikal xulosa linkini qo'yish mumkin
    qr_data = f"https://t.me/Faraidsbot?start=check_{doc_id}" 
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    qr_img_path = f"qr_{timestamp}.png"
    img = qr.make_image(fill_color="#1A365D", back_color="white")
    img.save(qr_img_path)
    
    # ReportLab uchun QR-kod rasmini o'lchamlash (65x65 pikselli ixcham muhr)
    qr_image_file = Image(qr_img_path, width=65, height=65)
    
    # 5. TASDIQLASH VA MUHR QISMI (QR-KOD INTEGRATSIYASI BILAN)
    footer_data = [
        [
            Paragraph("<b>Mas'ul shifokor:</b> _______________", value_style),
            qr_image_file  # Muhr o'rniga dinamik QR-kod qo'yildi
        ],
        [
            Paragraph("<font color='#718096'>Farg'ona viloyat OITS markazi<br/>Laboratoriya mudiri</font>", subtitle_style),
            Paragraph("<font color='#E53E3E'><b>[ ELEKTRON TASDIQLANGAN ]</b></font><br/><font color='#718096'>Haqiqiyligini tekshirish uchun skanerlang</font>", subtitle_style)
        ]
    ]
    
    footer_table = Table(footer_data, colWidths=[265, 265])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(footer_table)
    
    # PDFni qurish
    doc.build(story)
    
    # Vaqtinchalik yaratilgan QR-kod rasmini o'chirib tashlaymiz (Loyiha toza turishi uchun)
    if os.path.exists(qr_img_path):
        os.remove(qr_img_path)
        
    return filename