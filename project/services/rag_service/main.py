from fastapi import FastAPI

from shared.constants import HEALTH_PATH
from shared.schemas import HealthResponse, RAGAnswerRequest, RAGGenerateRequest, RAGResponse
from services.rag_service.rag_pipeline import generate_recommendations, answer_question
from shared.schemas import PDFGenerateRequest, PDFGenerateResponse
from services.rag_service.pdf_generator import generate_recommendation_pdf

app = FastAPI(
    title="RAG Service",
    description="Teşvik belgelerinden kaynaklı cevap ve açıklamalı öneri üretir.",
    version="1.0.0",
)


@app.get(HEALTH_PATH, response_model=HealthResponse)
async def health_check():
    return HealthResponse(service="rag_service", status="ok")


@app.post("/rag/generate", response_model=RAGResponse)
async def rag_generate(request: RAGGenerateRequest):
    return await generate_recommendations(request)


@app.post("/rag/answer", response_model=RAGResponse)
async def rag_answer(request: RAGAnswerRequest):
    return await answer_question(request)

@app.post("/rag/pdf", response_model=PDFGenerateResponse)
async def rag_pdf(request: PDFGenerateRequest):
    pdf_path = generate_recommendation_pdf(
        recommendation=request.recommendation,
        sources=request.sources,
    )

    return PDFGenerateResponse(
        success=True,
        message="PDF başarıyla oluşturuldu.",
        error=None,
        pdf_path=pdf_path,
    )