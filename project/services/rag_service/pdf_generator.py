import os
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

# Olası font yollarını tarıyoruz (Sistem yolu öncelikli)
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Docker sistemi altındaki resmi yol
    os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf")  # Yerel çalışma dizini
]

FONT_NAME = "Helvetica"  # Varsayılan fallback

for path in FONT_PATHS:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont("DejaVu", path))
            FONT_NAME = "DejaVu"
            logger.info(f"Yazı tipi başarıyla yüklendi: {path}")
            break
        except Exception as e:
            logger.error(f"Yazı tipi kaydı başarısız ({path}): {e}")

if FONT_NAME == "Helvetica":
    logger.warning("DejaVu yazı tipi sistemde bulunamadı. Türkçe karakter hataları oluşabilir.")


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

    # 3. İki Sütunlu Yapı (ReportLab içinde HTML listeler yerine daha kararlı satır sonu formatı kullanılmıştır)
    why_matched_text = "<br/>".join([f"• {item}" for item in recommendation.why_matched])
    eligibility_text = "<br/>".join([f"• {item}" for item in recommendation.eligibility_notes])
    
    col1_content = [
        Paragraph("Neden Eşleşti?", h2_style),
        Paragraph(why_matched_text, body_style)
    ]
    col2_content = [
        Paragraph("Kritik Şartlar & Uyarılar", h2_style),
        Paragraph(eligibility_text, body_style)
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
    steps_text = "<br/>".join([f"{i+1}. {step}" for i, step in enumerate(recommendation.application_steps)])
    story.append(Paragraph(steps_text, body_style))
    story.append(Spacer(1, 10))

    # 5. İstenen Belgeler
    story.append(Paragraph("İstenen Belgeler ve Formlar", h2_style))
    docs_text = "<br/>".join([f"• {doc}" for doc in recommendation.required_documents])
    story.append(Paragraph(docs_text, body_style))
    story.append(Spacer(1, 15))

    # 6. Atıfta Bulunulan Kaynaklar
    if sources:
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db"), spaceBefore=10, spaceAfter=10))
        story.append(Paragraph("Raporda Atıfta Bulunulan Kaynak Belgeler", h2_style))
        for idx, src in enumerate(sources):
            source_label = src.source_file or "Resmi Teşvik Dökümanı"
            story.append(Paragraph(f"[{idx+1}] {source_label} — Atıf Doğruluğu: %{int((src.score or 0) * 100)}", italic_style))
            story.append(Spacer(1, 3))

    # 7. Sorumluluk Reddi
    story.append(Spacer(1, 15))
    story.append(Paragraph(f"<i>* {recommendation.disclaimer}</i>", italic_style))

    doc.build(story)
    buffer.seek(0)
    return buffer