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
    # Kullanıcı mesajından niyet tespiti
    intent = detect_intent(
        message=request.message,
        user_profile=request.user_profile,
    )

    # 1. GREETING
    if intent.intent == IntentType.GREETING:
        return ChatResponse(
            success=True,
            message="Greeting response.",
            error=None,
            answer="Merhaba! Teşvik ve devlet destekleri programları hakkında size yardımcı olabilirim.",
            intent=intent,
            user_profile=request.user_profile,
            matches=request.current_matches,
            recommendations=request.current_recommendations,
            sources=[],
            conversation_id=request.conversation_id,
        )

    # 2. GENERAL INFO (Yeni Eklendi)
    if intent.intent == IntentType.GENERAL_INFO:
        return ChatResponse(
            success=True,
            message="Sistem bilgilendirme yanıtı.",
            error=None,
            answer=(
                "Ben devlet teşvikleri ve destek programları konusunda uzmanlaşmış dijital bir asistanım. "
                "Şirketinizin çalışan sayısı, cirosu ve ihtiyaçlarına en uygun KOSGEB, TÜBİTAK gibi "
                "destekleri saniyeler içinde analiz edebilirim. Bana şirketinizden bahsedebilir veya "
                "özel bir programın başvuru şartlarını sorabilirsiniz."
            ),
            intent=intent,
            user_profile=request.user_profile,
            matches=request.current_matches,
            recommendations=request.current_recommendations,
            sources=[],
            conversation_id=request.conversation_id,
        )

    # 3. OUT OF SCOPE (Yeni Eklendi)
    if intent.intent == IntentType.OUT_OF_SCOPE:
        return ChatResponse(
            success=True,
            message="Kapsam dışı yanıt.",
            error=None,
            answer=(
                "Bu konuda size yardımcı olamıyorum. Ben sadece devlet teşvikleri, "
                "hibeler ve destek programları konusunda uzmanlaşmış bir asistanım."
            ),
            intent=intent,
            user_profile=request.user_profile,
            matches=request.current_matches,
            recommendations=request.current_recommendations,
            sources=[],
            conversation_id=request.conversation_id,
        )

    # 4. RAG QUESTION
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

    # 5. ELIGIBILITY QUESTION (Yeni Eklendi)
    if intent.intent == IntentType.ELIGIBILITY_QUESTION:
        # Eğer zaten konuşulmuş/eşleşmiş destekler varsa doğrudan onlar üzerinde RAG çalıştır
        if request.current_matches:
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
                message="Uygunluk analizi üretildi.",
                error=None,
                answer=rag_response.answer,
                intent=intent,
                user_profile=request.user_profile,
                matches=request.current_matches,
                recommendations=request.current_recommendations,
                sources=rag_response.sources,
                conversation_id=request.conversation_id,
            )
        else:
            # Eşleşen destek yoksa ve profil eksikse bilgi iste
            if intent.needs_user_profile or request.user_profile is None:
                return ChatResponse(
                    success=True,
                    message="Eksik profil bilgisi var.",
                    error=None,
                    answer=(
                        "Herhangi bir programa uygunluğunuzu değerlendirebilmem için öncelikle şirket "
                        "bilgilerinize ihtiyacım var. Lütfen sektör, çalışan sayısı, "
                        "yıllık ciro ve ihtiyaç alanlarınızı paylaşın."
                    ),
                    intent=intent,
                    user_profile=request.user_profile,
                    matches=[],
                    recommendations=[],
                    sources=[],
                    conversation_id=request.conversation_id,
                )
            
            # Profil tamsa önce eşleştir, sonra uygunluk sorusunu RAG ile cevapla
            match_response = await call_matching_service(
                MatchRequest(
                    user_profile=request.user_profile,
                    top_k=5,
                )
            )
            
            rag_response = await call_rag_answer(
                RAGAnswerRequest(
                    user_message=request.message,
                    user_profile=request.user_profile,
                    current_matches=match_response.matches,
                    language=request.language,
                    top_k_chunks=5,
                )
            )
            
            return ChatResponse(
                success=True,
                message="Yeni uygunluk analizi üretildi.",
                error=None,
                answer=rag_response.answer,
                intent=intent,
                user_profile=request.user_profile,
                matches=match_response.matches,
                recommendations=request.current_recommendations,
                sources=rag_response.sources,
                conversation_id=request.conversation_id,
            )

    # 6. INCENTIVE RECOMMENDATION
    if intent.intent == IntentType.INCENTIVE_RECOMMENDATION:
        if intent.needs_user_profile or request.user_profile is None:
            return ChatResponse(
                success=True,
                message="Eksik profil bilgisi var.",
                error=None,
                answer=(
                    "Size en uygun teşvikleri listeleyebilmem için bazı bilgilere ihtiyacım var. "
                    "Lütfen sektör, çalışan sayısı, yıllık ciro ve ihtiyaç alanlarınızı paylaşın."
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

    # 7. PROFILE UPDATE (Yeni Eklendi)
    if intent.intent == IntentType.PROFILE_UPDATE:
        return ChatResponse(
            success=True,
            message="Profil güncelleniyor.",
            error=None,
            answer=(
                "Profil bilgilerinizi güncelleme talebinizi aldım. "
                "Lütfen yeni bilgilerinizi (çalışan sayısı, ciro vb.) girin. "
                "Bilgileriniz güncellendiğinde uygun destekleri tekrar listeleyebilirim."
            ),
            intent=intent,
            user_profile=request.user_profile,
            matches=request.current_matches,
            recommendations=request.current_recommendations,
            sources=[],
            conversation_id=request.conversation_id,
        )

    # 8. FALLBACK / UNKNOWN
    return ChatResponse(
        success=True,
        message="Intent net değil.",
        error=None,
        answer=(
            "Sorunuzu tam olarak anlayamadım. Teşvik programlarının başvuru şartlarını mı "
            "merak ediyorsunuz, yoksa şirketiniz için uygun bir destek bulmamı mı istersiniz? "
            "Lütfen daha açık ifade edebilir misiniz?"
        ),
        intent=intent,
        user_profile=request.user_profile,
        matches=request.current_matches,
        recommendations=request.current_recommendations,
        sources=[],
        conversation_id=request.conversation_id,
    )