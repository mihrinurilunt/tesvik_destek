import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from shared.exceptions import AppException
from shared.logger import get_logger
from shared.response_utils import error_message
from shared.schemas import RAGGenerateRequest, RAGAnswerRequest, RAGResponse, HealthResponse
from shared.constants import HEALTH_PATH, RAG_GENERATE_PATH, RAG_ANSWER_PATH

from services.rag_service.llm_client import call_llm_generate, call_llm_answer
from fastapi.responses import StreamingResponse
from shared.schemas import PDFGenerateRequest
from services.rag_service.pdf_generator import generate_recommendation_pdf

logger = get_logger(__name__)

app = FastAPI(
    title="RAG Service",
    description="Qdrant ve OpenAI destekli döküman sorgulama, akıllı fallback ve kişiselleştirilmiş teşvik analiz servisi.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"Uygulama Hatası: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_message(
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
        ),
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception("RAG Servisinde beklenmeyen sistem hatası")
    return JSONResponse(
        status_code=500,
        content=error_message(
            code="INTERNAL_SERVER_ERROR",
            message="RAG servisinde beklenmeyen bir sistem hatası oluştu.",
            details={"error": str(exc)},
        ),
    )


@app.get(HEALTH_PATH, response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        service="rag_service",
        status="ok",
    )

@app.post("/pdf/generate")
async def generate_pdf(request: PDFGenerateRequest):
    """
    Gelen analiz raporuna uygun PDF belgesi oluşturarak stream olarak döner.
    """
    logger.info("PDF generation request received")
    pdf_buffer = generate_recommendation_pdf(
        recommendation=request.recommendation,
        sources=request.sources
    )
    
    filename = f"tesvik_raporu_{request.recommendation.program_id}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post(RAG_GENERATE_PATH, response_model=RAGResponse)
async def rag_generate(request: RAGGenerateRequest):
    logger.info("RAG generate isteği alındı.")
    return await call_llm_generate(request)


@app.post(RAG_ANSWER_PATH, response_model=RAGResponse)
async def rag_answer(request: RAGAnswerRequest):
    logger.info("RAG answer isteği alındı.")
    return await call_llm_answer(request)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)