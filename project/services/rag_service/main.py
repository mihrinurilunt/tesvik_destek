import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from typing import List

# Shared katmanından resmi modelleri ve API sözleşmelerini çekiyoruz
from shared.schemas import RAGRequest, RAGResponse, ChatRequest, ChatResponse, HealthResponse
from shared.models import Recommendation

from retrieval import RagRetriever
from prompt_builder import PromptBuilder
from llm_client import LlmClient

app = FastAPI(title="Teşvik RAG Service", version="1.0.0")

retriever = RagRetriever()
llm = LlmClient()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """API Contract uyumlu sağlık kontrolü."""
    return HealthResponse(service="rag_service", status="ok")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """API Contract uyumlu standart sohbet yanıtı."""
    try:
        # 1. Qdrant'tan bağlamı getir
        context = retriever.retrieve_context(req.message, req.program_name)
        
        # 2. Prompt oluştur
        prompt = PromptBuilder.build_chat_prompt(req.message, context)
        
        # 3. LLM'den yanıt al
        answer = llm.generate_complete(prompt)
        
        # 4. Kaynakları listele
        sources = [req.program_name] if req.program_name else []
        
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Arayüzün canlı (streaming) yazma efekti yapabilmesi için akış kanalı."""
    try:
        context = retriever.retrieve_context(req.message, req.program_name)
        prompt = PromptBuilder.build_chat_prompt(req.message, context)
        
        def event_generator():
            for chunk in llm.generate_stream(prompt):
                yield chunk
                
        return StreamingResponse(event_generator(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate", response_model=RAGResponse)
def generate_report(req: RAGRequest):
    """Eşleşen desteklerin resmi belgelerini RAG ile tarayarak detaylı analiz üretir."""
    try:
        recommendations = []
        
        # Her bir eşleşen program için RAG analizi yapıyoruz
        for match in req.matches:
            # Qdrant'tan döküman parçalarını çek (Zorunlu alanlar taranır)
            context = retriever.retrieve_context(
                query="amaç başvuru şartları gerekli belgeler ve adımlar", 
                program_name=match.program_name, 
                top_k=req.top_k_chunks
            )
            
            # Prompt oluştur
            prompt = PromptBuilder.build_generation_prompt(match.program_name) + f"\n\nBağlam: {context}"
            
            # LLM'den yapılandırılmış JSON çıktısını al
            raw_response = llm.generate_complete(prompt)
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            veri = json.loads(clean_json)
            
            # Gelen veriyi Recommendation sözleşmesine göre güvenli şekilde sarmalıyoruz
            # (Metadatalar uydurmayı önlemek için doğrudan Matching çıktısından beslenir)
            rec = Recommendation(
                program_id=match.program_id,
                program_name=match.program_name,
                institution=match.institution,
                score=match.score,
                summary=veri.get("amaci", "Program analiz dökümanı başarıyla oluşturulmuştur."),
                why_matched=match.match_reasons if match.match_reasons else ["Profiliniz program kriterlerine uygundur."],
                application_steps=veri.get("adimlar", ["Online başvuru yapılması"]),
                required_documents=veri.get("belgeler", ["Güncel evrak listesi"]),
                application_url=match.application_url,
                disclaimer="Bu sonuç bilgilendirme amaçlıdır. Güncel ve resmî koşullar için kurumun resmî sayfasını kontrol edin.",
                source_urls=[match.application_url] if match.application_url else []
            )
            recommendations.append(rec)
            
        return RAGResponse(
            success=True,
            message="Recommendations generated successfully",
            recommendations=recommendations
        )
    except Exception as e:
        # API Contract standardına uygun hata yanıtı yapısı
        return RAGResponse(
            success=False,
            message=f"RAG raporu üretilirken hata oluştu: {str(e)}",
            recommendations=[]
        )