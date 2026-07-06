import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from shared.exceptions import AppException
from shared.logger import get_logger
from shared.response_utils import error_message
from shared.schemas import (
    RAGGenerateRequest, 
    RAGAnswerRequest, 
    RAGResponse, 
    HealthResponse, 
    PDFGenerateRequest
)
from shared.constants import HEALTH_PATH, RAG_GENERATE_PATH, RAG_ANSWER_PATH

from services.rag_service.llm_client import call_llm_generate, call_llm_answer
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
    logger.error(f"Uygulama Hatası: {exc.message} (Kod: {exc.error_code})")
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
    logger.exception("RAG Servisinde beklenmeyen sistem hatası meydana geldi")
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
    logger.debug("RAG Service sağlık kontrolü tetiklendi.")
    return HealthResponse(
        service="rag_service",
        status="ok",
    )


@app.post("/pdf/generate")
async def generate_pdf(request: PDFGenerateRequest):
    """
    Gelen kişiselleştirilmiş analiz raporu ve ilgili kaynak belgelerine uygun 
    resmi PDF raporunu oluşturur ve stream (akış) olarak döner.
    """
    logger.info(f"PDF üretim isteği alındı. Program ID: {request.recommendation.program_id}")
    try:
        # Önceki adımlarda düzelttiğimiz temiz kaynak bilgileri doğrudan PDF jeneratörüne aktarılır
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
    except Exception as e:
        logger.error(f"PDF raporu üretilirken hata oluştu: {e}")
        return JSONResponse(
            status_code=500,
            content=error_message(
                code="PDF_GENERATION_FAILED",
                message="PDF raporu oluşturulamadı.",
                details={"error": str(e)}
            )
        )


@app.post(RAG_GENERATE_PATH, response_model=RAGResponse)
async def rag_generate(request: RAGGenerateRequest):
    """
    Eşleşen teşvikleri analiz ederek paralel asenkron RAG raporu üretir.
    """
    logger.info(f"Paralel RAG üretimi tetiklendi. Eşleşme sayısı: {len(request.matches)}")
    return await call_llm_generate(request)


@app.post(RAG_ANSWER_PATH, response_model=RAGResponse)
async def rag_answer(request: RAGAnswerRequest):
    """
    Kullanıcının genel veya belirli bir teşvik odaklı sorusuna bağlamsal RAG yanıtı üretir.
    """
    logger.info("Doğrudan RAG soru-cevap akışı tetiklendi.")
    return await call_llm_answer(request)


if __name__ == "__main__":
    # Servis yerel ağda 8002 portu üzerinden yayına başlar
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)