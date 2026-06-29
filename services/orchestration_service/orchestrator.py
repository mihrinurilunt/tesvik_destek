from shared.enums import IntentType, TargetService
from shared.schemas import (
    ChatRequest,
    ChatResponse,
    IntentResult,
    RecommendationRequest,
    RecommendationResponse,
)


async def handle_recommendation(
    request: RecommendationRequest,
) -> RecommendationResponse:
    return RecommendationResponse(
        success=True,
        message="Recommendation endpoint is working.",
        error=None,
        answer="Form bilgileriniz alındı. Matching ve RAG bağlantısı sonraki adımda eklenecek.",
        user_profile=request.user_profile,
        matches=[],
        recommendations=[],
        sources=[],
        conversation_id=request.conversation_id,
    )


async def handle_chat(request: ChatRequest) -> ChatResponse:
    intent = IntentResult(
        intent=IntentType.GREETING,
        confidence=1.0,
        is_in_scope=True,
        needs_user_profile=False,
        target_service=TargetService.NONE,
        reason="Test amaçlı varsayılan intent.",
    )

    return ChatResponse(
        success=True,
        message="Chat endpoint is working.",
        error=None,
        answer="Mesajınız alındı. Intent manager sonraki adımda bağlanacak.",
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
    )