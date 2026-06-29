import os
import urllib.request
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from shared.models import Recommendation, SourceChunk
from shared.logger import get_logger

logger = get_logger(__name__)

# Font Dosya Yolu ve Otomatik İndirme Mekanizması
FONT_PATH = os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")

if not os.path.exists(FONT_PATH):
    try:
        logger.info("DejaVuSans.ttf bulunamadı. Türkçe karakter desteği için font otomatik indiriliyor...")
        # Font dosyasını güvenli bir kaynaktan indiriyoruz
        url = "https://raw.githubusercontent.com/scholer/ensm-font-dejavu/master/DejaVuSans.ttf"
        urllib.request.urlretrieve(url, FONT_PATH)
        logger.info("DejaVuSans.ttf başarıyla indirildi.")
    except Exception as e:
        logger.error(f"Font dosyası indirilirken hata oluştu: {e}")

# Font Kaydı
if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))
        FONT_NAME = "DejaVu"
    except Exception as e:
        logger.error(f"Font kaydedilemedi: {e}")
        FONT_NAME = "Helvetica"
else:
    FONT_NAME = "Helvetica"


def generate_recommendation_pdf(recommendation: Recommendation, sources: list[SourceChunk]) -> BytesIO:
    """
    Öneri raporunu ve atıfta bulunulan kaynakları içeren profesyonel bir PDF oluşturur.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Heading1"],
        fontName=FONT_NAME,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        "PDFSubtitle",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4b5563"),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        "PDFH2",
        parent=styles["Heading2"],
        fontName=FONT_NAME,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        "PDFBody",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#374151")
    )

    italic_style = ParagraphStyle(
        "PDFItalic",
        parent=body_style,
        fontName=FONT_NAME,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#6b7280")
    )

    story = []

    # 1. Başlık Alanı
    story.append(Paragraph(recommendation.program_name, title_style))
    story.append(Paragraph(f"Kurum: {recommendation.institution}  |  Uyum Skoru: %{int(recommendation.score)}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e5e7eb"), spaceAfter=15))

    # 2. Özet
    story.append(Paragraph("Program Özeti", h2_style))
    story.append(Paragraph(recommendation.summary, body_style))
    story.append(Spacer(1, 10))

    # 3. İki Sütunlu Yapı: Neden Eşleşti & Kritik Şartlar
    why_matched_html = "".join([f"<li>{item}</li>" for item in recommendation.why_matched])
    eligibility_html = "".join([f"<li>{item}</li>" for item in recommendation.eligibility_notes])
    
    col1_content = [
        Paragraph("Neden Eşleşti?", h2_style),
        Paragraph(f"<ul>{why_matched_html}</ul>", body_style)
    ]
    col2_content = [
        Paragraph("Kritik Şartlar & Uyarılar", h2_style),
        Paragraph(f"<ul>{eligibility_html}</ul>", body_style)
    ]

    table_data = [[col1_content, col2_content]]
    col_width = [255, 255]
    t = Table(table_data, colWidths=col_width)
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # 4. Başvuru Adımları
    story.append(Paragraph("Başvuru Adımları", h2_style))
    steps_html = "".join([f"<li>{step}</li>" for step in recommendation.application_steps])
    story.append(Paragraph(f"<ol>{steps_html}</ol>", body_style))
    story.append(Spacer(1, 10))

    # 5. İstenen Belgeler
    story.append(Paragraph("İstenen Belgeler ve Formlar", h2_style))
    docs_html = "".join([f"<li>{doc}</li>" for doc in recommendation.required_documents])
    story.append(Paragraph(f"<ul>{docs_html}</ul>", body_style))
    story.append(Spacer(1, 15))

    # 6. Atıfta Bulunulan Kaynaklar (RAG Sources)
    if sources:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db"), spaceBefore=10, spaceAfter=10))
        story.append(Paragraph("Raporda Atıfta Bulunulan Kaynak Belgeler", h2_style))
        for idx, src in enumerate(sources):
            source_label = src.source_file or "Resmi Teşvik Dökümanı"
            story.append(Paragraph(f"[{idx+1}] {source_label} — Atıf Doğruluğu: %{int((src.score or 0) * 100)}", italic_style))
            story.append(Spacer(1, 3))

    # 7. Sorumluluk Reddi (Disclaimer)
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<i>* {recommendation.disclaimer}</i>", italic_style))

    doc.build(story)
    buffer.seek(0)
    return buffer