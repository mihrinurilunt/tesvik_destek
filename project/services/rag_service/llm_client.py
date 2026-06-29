import os
import json
from typing import List
from openai import AsyncOpenAI
from pydantic import HttpUrl

from shared.config import settings
from shared.models import UserProfile, MatchResult, Recommendation
from shared.schemas import RAGGenerateRequest, RAGAnswerRequest, RAGResponse
from shared.logger import get_logger

from services.rag_service.retrieval import retrieve_chunks
from services.rag_service.prompt_builder import (
    build_recommendation_prompt,
    build_overall_answer_prompt,
    build_answer_prompt,
)

logger = get_logger(__name__)

OPENAI_API_KEY = getattr(settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def generate_recommendation_for_match(
    profile: UserProfile,
    match: MatchResult,
    top_k_chunks: int = 3
) -> Recommendation:
    """
    Qdrant'tan aldığı bağlam dökümanları ile LLM'i çağırarak kişiselleştirilmiş hibe önerisi oluşturur.
    """
    chunks = await retrieve_chunks(
        query_text=match.program_name,
        top_k=top_k_chunks,
        program_id=match.program_id
    )
    
    context_text = "\n\n".join([f"--- Chunk {i+1} ---\n{c.text}" for i, c in enumerate(chunks)])
    prompt = build_recommendation_prompt(profile, match, context_text)
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Yalnızca şemaya uygun, geçerli saf JSON formatında yanıt veren bir yardımcı modülsün."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        raw_content = response.choices[0].message.content or "{}"
        data = json.loads(raw_content)
        
        source_urls = []
        for c in chunks:
            if c.source_url and c.source_url not in source_urls:
                source_urls.append(c.source_url)
                
        return Recommendation(
            program_id=match.program_id,
            program_name=match.program_name,
            institution=match.institution,
            score=match.score,
            summary=data.get("summary", f"{match.program_name} programı firmanız için önerilmektedir."),
            why_matched=data.get("why_matched") or match.match_reasons or ["Profiliniz hibe programı ile uyumlu bulunmuştur."],
            eligibility_notes=data.get("eligibility_notes") or match.missing_criteria or ["Genel başvuru kriterlerini kontrol ediniz."],
            application_steps=data.get("application_steps") or ["Kurum portalı üzerinden başvuruyu başlatın."],
            required_documents=data.get("required_documents") or ["Gerekli kurumsal belgeler."],
            application_url=match.application_url,
            source_urls=source_urls,
            sources=chunks,
            disclaimer="Bu öneriler bilgilendirme amaçlıdır; resmi uygunluk veya başvuru garantisi vermez."
        )
    except Exception as e:
        logger.error(f"Recommendation oluşturulurken LLM hatası ({match.program_id}): {e}")
        return Recommendation(
            program_id=match.program_id,
            program_name=match.program_name,
            institution=match.institution,
            score=match.score,
            summary=f"{match.program_name} programı şirketiniz için uygun bulunmuştur.",
            why_matched=match.match_reasons or ["Genel profil uyumu sağlandı."],
            eligibility_notes=match.missing_criteria or ["Şartları kontrol ediniz."],
            application_steps=["Resmi kanallar üzerinden başvuru sürecini başlatın."],
            required_documents=["Standart başvuru belgeleri."],
            application_url=match.application_url,
            sources=chunks
        )


async def call_llm_generate(request: RAGGenerateRequest) -> RAGResponse:
    """
    /rag/generate akışını yönetir. Tüm teşvikler için detaylı analiz raporları oluşturur.
    """
    recommendations = []
    all_sources = []
    
    # Token limitlerini korumak için ilk 5 eşleşme işleme alınır
    for match in request.matches[:5]:
        rec = await generate_recommendation_for_match(
            profile=request.user_profile,
            match=match,
            top_k_chunks=request.top_k_chunks
        )
        recommendations.append(rec)
        all_sources.extend(rec.sources)
        
    # Yinelenen kaynakların ayıklanması
    seen_chunks = set()
    deduped_sources = []
    for src in all_sources:
        if src.chunk_id not in seen_chunks:
            seen_chunks.add(src.chunk_id)
            deduped_sources.append(src)
            
    overall_answer = ""
    if recommendations:
        prompt = build_overall_answer_prompt(request.user_profile, recommendations)
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Sen cana yakın ve profesyonel bir teşvik danışmanısın."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6
            )
            overall_answer = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Genel cevap oluşturulurken LLM hatası: {e}")
            overall_answer = "Şirketiniz için en uygun bulduğumuz hibe programları aşağıda listelenmiştir."
            
    return RAGResponse(
        success=True,
        answer=overall_answer,
        recommendations=recommendations,
        sources=deduped_sources
    )


async def call_llm_answer(request: RAGAnswerRequest) -> RAGResponse:
    """
    /rag/answer akışını yönetir. Döküman bağlamına dayalı veya fallback ile yanıt döner.
    """
    chunks = await retrieve_chunks(
        query_text=request.user_message,
        top_k=request.top_k_chunks
    )
    
    context_text = ""
    if chunks:
        context_text = "\n\n".join(
            [f"--- Kaynak {i+1} (Belge: {c.program_name or 'Belirtilmemiş'}) ---\n{c.text}" for i, c in enumerate(chunks)]
        )
    else:
        context_text = "Veritabanında doğrudan eşleşen bir döküman bulunamadı."
        
    prompt = build_answer_prompt(request.user_message, context_text, request.user_profile)
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sen dürüst ve resmi bir devlet destekleri uzmanı asistanısın."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        answer = response.choices[0].message.content or "Sorunuz şu an işlenemedi."
        
        return RAGResponse(
            success=True,
            answer=answer,
            recommendations=[],
            sources=chunks
        )
    except Exception as e:
        logger.error(f"Soru-cevap sürecinde LLM hatası: {e}")
        return RAGResponse(
            success=False,
            answer="Sorunuzu işlerken teknik bir problem yaşandı. Lütfen daha sonra tekrar deneyiniz.",
            recommendations=[],
            sources=[]
        )