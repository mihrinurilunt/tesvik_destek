from shared.enums import IntentType
from shared.schemas import (
    ChatRequest,
    ChatResponse,
    MatchRequest,
    RAGAnswerRequest,
    RAGGenerateRequest,
    RecommendationRequest,
    RecommendationResponse,
)

from services.orchestration_service.intent_manager import detect_intent
from services.orchestration_service.service_clients import (
    call_matching_service,
    call_rag_answer,
    call_rag_generate,
)


async def handle_recommendation(
    request: RecommendationRequest,
) -> RecommendationResponse:
    match_response = await call_matching_service(
        MatchRequest(
            user_profile=request.user_profile,
            top_k=request.top_k,
        )
    )

    if not match_response.matches:
        return RecommendationResponse(
            success=True,
            message="Uygun destek bulunamadı.",
            error=None,
            answer="Profilinize göre uygun teşvik/destek bulunamadı.",
            user_profile=request.user_profile,
            matches=[],
            recommendations=[],
            sources=[],
            conversation_id=request.conversation_id,
        )

    rag_response = await call_rag_generate(
        RAGGenerateRequest(
            user_profile=request.user_profile,
            matches=match_response.matches,
            user_message=None,
            language=request.language,
            top_k_chunks=5,
        )
    )

    return RecommendationResponse(
        success=True,
        message="Öneriler başarıyla oluşturuldu.",
        error=None,
        answer=rag_response.answer,
        user_profile=request.user_profile,
        matches=match_response.matches,
        recommendations=rag_response.recommendations,
        sources=rag_response.sources,
        conversation_id=request.conversation_id,
    )


async def handle_chat(request: ChatRequest) -> ChatResponse:
    intent = detect_intent(
        message=request.message,
        user_profile=request.user_profile,
    )

    if intent.intent == IntentType.GREETING:
        return ChatResponse(
            success=True,
            message="Greeting response.",
            error=None,
            answer="Merhaba, teşvik ve destek programları hakkında size yardımcı olabilirim.",
            intent=intent,
            user_profile=request.user_profile,
            matches=request.current_matches,
            recommendations=request.current_recommendations,
            sources=[],
            conversation_id=request.conversation_id,
        )

    if intent.intent == IntentType.RAG_QUESTION:
        rag_response = await call_rag_answer(
            RAGAnswerRequest(
                user_message=request.message,
                user_profile=request.user_profile,
                current_matches=request.current_matches,
                language=request.language,
                top_k_chunks=5,
            )
        )

        return ChatResponse(
            success=True,
            message="RAG cevabı üretildi.",
            error=None,
            answer=rag_response.answer,
            intent=intent,
            user_profile=request.user_profile,
            matches=request.current_matches,
            recommendations=request.current_recommendations,
            sources=rag_response.sources,
            conversation_id=request.conversation_id,
        )

    if intent.intent == IntentType.INCENTIVE_RECOMMENDATION:
        if intent.needs_user_profile or request.user_profile is None:
            return ChatResponse(
                success=True,
                message="Eksik profil bilgisi var.",
                error=None,
                answer=(
                    "Size uygun teşvikleri bulabilmem için sektör, çalışan sayısı, "
                    "yıllık ciro ve ihtiyaç alanlarını paylaşmanız gerekiyor."
                ),
                intent=intent,
                user_profile=request.user_profile,
                matches=[],
                recommendations=[],
                sources=[],
                conversation_id=request.conversation_id,
            )

        recommendation_response = await handle_recommendation(
            RecommendationRequest(
                user_profile=request.user_profile,
                top_k=5,
                language=request.language,
                conversation_id=request.conversation_id,
            )
        )

        return ChatResponse(
            success=True,
            message="Chat üzerinden öneriler oluşturuldu.",
            error=None,
            answer=recommendation_response.answer,
            intent=intent,
            user_profile=request.user_profile,
            matches=recommendation_response.matches,
            recommendations=recommendation_response.recommendations,
            sources=recommendation_response.sources,
            conversation_id=request.conversation_id,
        )

    return ChatResponse(
        success=True,
        message="Intent net değil.",
        error=None,
        answer="Sorunuzu biraz daha açık yazar mısınız? Örneğin destek adı, başvuru şartı veya gerekli belgeleri sorabilirsiniz.",
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
    )