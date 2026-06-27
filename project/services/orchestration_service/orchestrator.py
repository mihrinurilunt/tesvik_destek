from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.constants import (
    CHAT_PATH,
    HEALTH_PATH,
    ORCHESTRATION_SERVICE_NAME,
    RECOMMEND_PATH,
)
from shared.exceptions import AppException
from shared.logger import get_logger
from shared.response_utils import error_message
from shared.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    RecommendationRequest,
    RecommendationResponse,
)

logger = get_logger(__name__)

app = FastAPI(
    title="Orchestration Service",
    description=(
        "Frontend'den gelen form ve chat isteklerini alır; "
        "matching_service ve rag_service akışlarını yönetir."
    ),
    version="0.1.0",
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"Application error: {exc.message}")

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
    logger.exception("Unexpected error occurred")

    return JSONResponse(
        status_code=500,
        content=error_message(
            code="INTERNAL_SERVER_ERROR",
            message="Beklenmeyen bir hata oluştu.",
            details={"service": ORCHESTRATION_SERVICE_NAME},
        ),
    )


@app.get(HEALTH_PATH, response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        service=ORCHESTRATION_SERVICE_NAME,
        status="ok",
    )


@app.post(RECOMMEND_PATH, response_model=RecommendationResponse)
async def recommend(request: RecommendationRequest):
    """
    Formdan gelen kullanıcı profiliyle öneri üretme endpointi.

    Akış:
    1. Frontend RecommendationRequest gönderir.
    2. Orchestration service bunu MatchRequest'e çevirip matching_service'e gönderecek.
    3. Matching sonucu MatchResponse olarak alınacak.
    4. Match varsa RAGGenerateRequest oluşturulup rag_service'e gönderilecek.
    5. Frontend'e RecommendationResponse dönecek.

    Şimdilik dummy response dönüyor.
    Sonraki adımda bu fonksiyon orchestrator.handle_recommendation'a bağlanacak.
    """

    logger.info("Recommendation request received")

    return RecommendationResponse(
        success=True,
        message="Recommendation endpoint is working. Orchestrator will be connected next.",
        error=None,
        answer=(
            "Form bilgileriniz alındı. Bir sonraki adımda matching_service ve "
            "rag_service bağlantısı eklenecek."
        ),
        user_profile=request.user_profile,
        matches=[],
        recommendations=[],
        sources=[],
        conversation_id=request.conversation_id,
    )


@app.post(CHAT_PATH, response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat mesajı endpointi.

    Akış:
    1. Frontend ChatRequest gönderir.
    2. Intent Manager mesajın niyetini belirleyecek.
    3. Intent'e göre:
       - greeting ise hazır cevap
       - incentive_recommendation ise matching + rag/generate
       - rag_question ise rag/answer
       - eligibility_question ise mevcut match veya yeni matching + rag
       - out_of_scope ise kapsam dışı cevap
    4. Frontend'e ChatResponse dönecek.

    Şimdilik dummy response dönüyor.
    Sonraki adımda bu fonksiyon orchestrator.handle_chat'e bağlanacak.
    """

    logger.info("Chat request received")

    return ChatResponse(
        success=True,
        message="Chat endpoint is working. Intent manager will be connected next.",
        error=None,
        answer=(
            "Mesajınız alındı. Bir sonraki adımda intent manager, matching ve RAG "
            "akışı bağlanacak."
        ),
        intent=None,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
    )