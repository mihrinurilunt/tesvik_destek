from pathlib import Path
from uuid import uuid4

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from shared.models import Recommendation, SourceChunk


PDF_OUTPUT_DIR = Path("generated_pdfs")
PDF_OUTPUT_DIR.mkdir(exist_ok=True)


def generate_recommendation_pdf(
    recommendation: Recommendation,
    sources: list[SourceChunk],
) -> str:
    file_name = f"{recommendation.program_id}_{uuid4().hex[:8]}.pdf"
    file_path = PDF_OUTPUT_DIR / file_name

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Teşvik / Destek Programı Detay Raporu", styles["Title"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph(f"<b>Program Adı:</b> {recommendation.program_name}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Kurum:</b> {recommendation.institution}", styles["BodyText"]))
    story.append(Paragraph(f"<b>Uygunluk Skoru:</b> {recommendation.score}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Özet</b>", styles["Heading2"]))
    story.append(Paragraph(recommendation.summary, styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Neden Uygun Görünüyor?</b>", styles["Heading2"]))
    for item in recommendation.why_matched:
        story.append(Paragraph(f"- {item}", styles["BodyText"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Uygunluk Notları</b>", styles["Heading2"]))
    if recommendation.eligibility_notes:
        for item in recommendation.eligibility_notes:
            story.append(Paragraph(f"- {item}", styles["BodyText"]))
    else:
        story.append(Paragraph("Belirgin eksik kriter bulunamadı.", styles["BodyText"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Başvuru Adımları</b>", styles["Heading2"]))
    if recommendation.application_steps:
        for item in recommendation.application_steps:
            story.append(Paragraph(f"- {item}", styles["BodyText"]))
    else:
        story.append(Paragraph("Başvuru adımları kaynaklarda net olarak bulunamadı.", styles["BodyText"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Gerekli Belgeler</b>", styles["Heading2"]))
    if recommendation.required_documents:
        for item in recommendation.required_documents:
            story.append(Paragraph(f"- {item}", styles["BodyText"]))
    else:
        story.append(Paragraph("Gerekli belgeler kaynaklarda net olarak bulunamadı.", styles["BodyText"]))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Kaynaklar</b>", styles["Heading2"]))
    for index, source in enumerate(sources, start=1):
        story.append(
            Paragraph(
                f"{index}. {source.program_name or recommendation.program_name} - "
                f"{source.source_file or source.source_url or 'Kaynak bilgisi yok'}",
                styles["BodyText"],
            )
        )

    story.append(Spacer(1, 16))
    story.append(Paragraph(recommendation.disclaimer, styles["Italic"]))

    doc.build(story)

    return str(file_path)