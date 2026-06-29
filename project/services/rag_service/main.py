from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from services.rag_service.retrieval import RetrievalService
from services.rag_service.prompt_builder import PromptBuilder
from services.rag_service.llm_client import LLMClient

from shared.exceptions import AppException
from shared.logger import get_logger
from shared.response_utils import error_message
from shared.schemas import (
    RAGGenerateRequest,
    RAGAnswerRequest,
    RAGResponse,
    HealthResponse
)

logger = get_logger(__name__)

app = FastAPI(
    title="RAG Service",
    description="Qdrant döküman entegrasyonu ve LLM ile teşvik açıklaması üretme servisi.",
    version="1.0.0"
)

# Servis bağımlılıkları başlatılıyor
retrieval_service = RetrievalService()
llm_client = LLMClient()


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_message(code=exc.error_code, message=exc.message, details=exc.details)
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(service="rag_service", status="ok")


@app.post("/rag/generate", response_model=RAGResponse)
async def rag_generate(request: RAGGenerateRequest):
    """
    Formdan gelen veya eşleşen desteklerin detaylı analizini yapar.
    Adım adım başvuru kılavuzu hazırlar (PDF üretimi için hazırdır).
    """
    logger.info("RAG Generate isteği alındı.")
    try:
        program_ids = [m.program_id for m in request.matches]
        
        # 1. Eşleşen programlara ait detay dökümanlarını Qdrant'tan getiriyoruz
        # 'query' olarak kullanıcının ihtiyaç alanlarını birleştirip arama terimi yapabiliriz
        search_query = " ".join(request.user_profile.needs)
        chunks = await retrieval_service.retrieve_relevant_chunks(
            query=search_query,
            program_ids=program_ids,
            top_k=request.top_k_chunks
        )

        # 2. Promptları oluşturuyoruz
        system_prompt = PromptBuilder.build_generation_system_prompt(request.language)
        user_prompt = PromptBuilder.build_generation_user_prompt(
            user_profile=request.user_profile,
            matches=request.matches,
            contexts=chunks
        )

        # 3. LLM ile yapılandırılmış veriyi üretiyoruz
        summary, recommendations = await llm_client.generate_structured_recommendations(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # Her bir Recommendation nesnesine ilgili kaynak dökümanları bağlıyoruz
        for rec in recommendations:
            rec.sources = [c for c in chunks if c.program_id == rec.program_id]

        return RAGResponse(
            success=True,
            message="Öneriler başarıyla detaylandırıldı.",
            answer=summary,
            recommendations=recommendations,
            sources=chunks
        )

    except Exception as e:
        logger.exception("RAG Generate akışında beklenmeyen hata")
        return RAGResponse(
            success=False,
            message=f"Hata oluştu: {str(e)}",
            answer="Teşvik detayları hazırlanırken teknik bir problem yaşandı.",
            recommendations=[],
            sources=[]
        )


@app.post("/rag/answer", response_model=RAGResponse)
async def rag_answer(request: RAGAnswerRequest):
    """
    Kullanıcının chat içerisinden sorduğu soruları (Örn: 'KOSGEB için hangi belgeler lazım?')
    Qdrant dökümanlarına bakarak doğal dille cevaplar.
    """
    logger.info(f"RAG Answer isteği alındı: {request.user_message}")
    try:
        # Eğer chat'te mevcut konuşmada eşleşen programlar varsa arama önceliğini onlara veriyoruz
        program_ids = [m.program_id for m in request.current_matches] if request.current_matches else None

        # 1. Soruya en yakın kılavuz parçalarını Qdrant'tan aratıyoruz
        chunks = await retrieval_service.retrieve_relevant_chunks(
            query=request.user_message,
            program_ids=program_ids,
            top_k=request.top_k_chunks
        )

        # 2. Promptları hazırlıyoruz
        system_prompt = PromptBuilder.build_answer_system_prompt(request.language)
        user_prompt = PromptBuilder.build_answer_user_prompt(
            user_message=request.user_message,
            contexts=chunks,
            user_profile=request.user_profile
        )

        # 3. LLM yanıtı üretiyoruz
        answer = await llm_client.generate_text_answer(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        return RAGResponse(
            success=True,
            message="Soru başarıyla cevaplandı.",
            answer=answer,
            recommendations=[],
            sources=chunks # Kullanıcıya hangi döküman parçalarından faydalandığımızı kaynak (metadata) olarak dönüyoruz
        )

    except Exception as e:
        logger.exception("RAG Answer akışında beklenmeyen hata")
        return RAGResponse(
            success=False,
            message=f"Hata oluştu: {str(e)}",
            answer="Sorunuzu cevaplarken teknik bir problem yaşandı.",
            recommendations=[],
            sources=[]
        )