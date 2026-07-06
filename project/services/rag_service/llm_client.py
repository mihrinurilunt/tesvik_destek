import os
import json
import asyncio  # Asenkron paralel yönetim için
from typing import List, Optional
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
    # retrieval.py içindeki güncellenmiş retrieve_chunks'ı çağırıyoruz (Akıllı dosya adı üretimi içerir)
    chunks = await retrieve_chunks(
        query_text=match.program_name,
        top_k=top_k_chunks,
        program_id=match.program_id
    )
    
    # LLM'e giden chunk başlıklarında artık program_name yerine arayüze de yansıyan dinamik c.source_file değerini kullanıyoruz
    context_text = "\n\n".join([f"--- Kaynak {i+1} (Belge: {c.source_file or 'Teşvik Kılavuzu'}) ---\n{c.text}" for i, c in enumerate(chunks)])
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
            sources=chunks,  # Bu sayede chunk'lar (ve içindeki doğru source_file alanları) taşınır
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
    Eşleşen tüm programları paralel (asyncio.gather) olarak işleyerek
    sistem gecikmesini (latency) minimuma indirir.
    """
    logger.info(f"Paralel RAG üretimi başlatılıyor. Program sayısı: {len(request.matches)}")
    
    # İlk 5 eşleşmeyi paralel görevler olarak hazırlıyoruz
    tasks = [
        generate_recommendation_for_match(
            profile=request.user_profile,
            match=match,
            top_k_chunks=request.top_k_chunks
        )
        for match in request.matches[:5]
    ]
    
    # Tüm OpenAI/RAG isteklerini asenkron paralel olarak tetikliyoruz
    recommendations = await asyncio.gather(*tasks)
    
    all_sources = []
    for rec in recommendations:
        all_sources.extend(rec.sources)
        
    # Yinelenen kaynakların temizlenmesi (chunk_id bazlı)
    seen_chunks = set()
    deduped_sources = []
    for src in all_sources:
        if src.chunk_id not in seen_chunks:
            seen_chunks.add(src.chunk_id)
            deduped_sources.append(src)
            
    # Genel değerlendirme metninin hazırlanması
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
            logger.error(f"Genel cevap LLM üretim hatası: {e}")
            overall_answer = "Şirketiniz için en uygun bulduğumuz devlet hibe ve destek programları aşağıda detaylandırılmıştır."
            
    return RAGResponse(
        success=True,
        answer=overall_answer,
        recommendations=recommendations,
        sources=deduped_sources
    )


async def call_llm_answer(request: RAGAnswerRequest) -> RAGResponse:
    """
    Kullanıcı sorusuna bağlamsal veya genel yanıt üretir.
    """
    program_id = None
    focused_program_name = None
    query_text = request.user_message
    
    # Odaklanılmış tek bir program var mı kontrol et
    if request.current_matches and len(request.current_matches) == 1:
        program_id = request.current_matches[0].program_id
        focused_program_name = request.current_matches[0].program_name
        logger.info(f"RAG odaklanılan program: '{focused_program_name}' (ID: {program_id})")
        
        # SORGU ZENGİNLEŞTİRME (Query Enrichment)
        query_text = f"{focused_program_name} - {request.user_message}"

    # Retrieval aşamasına filtrelenmiş veya zenginleştirilmiş sorguyu paslıyoruz
    chunks = await retrieve_chunks(
        query_text=query_text,
        top_k=request.top_k_chunks,
        program_id=program_id
    )
    
    context_text = ""
    if chunks:
        context_text = "\n\n".join(
            [f"--- Kaynak {i+1} (Belge: {c.source_file or 'Belirtilmemiş'}) ---\n{c.text}" for i, c in enumerate(chunks)]
        )
    else:
        context_text = "Veritabanında doğrudan eşleşen herhangi bir resmi döküman kaydı bulunamadı."
        
    prompt = build_answer_prompt(
        user_message=request.user_message,
        context_text=context_text, 
        profile=request.user_profile,
        focused_program_name=focused_program_name
    )
    
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sen dürüst, resmi ve her zaman gerçekçi bir asistanısın."},
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
        logger.error(f"Answer LLM üretim hatası: {e}")
        return RAGResponse(
            success=False,
            answer="Üzgünüm, sorunuzu işlerken teknik bir problem yaşandı. Lütfen daha sonra tekrar deneyiniz.",
            recommendations=[],
            sources=[]
        )