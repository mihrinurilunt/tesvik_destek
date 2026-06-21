import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

# Yazdığımız modülleri içe aktarıyoruz
from retrieval import RagRetriever
from prompt_builder import PromptBuilder
from llm_client import LlmClient

app = FastAPI(title="Teşvik RAG Service", version="1.0.0")

# Sorumlu sınıfları başlatıyoruz
retriever = RagRetriever()
llm = LlmClient()

class ChatRequest(BaseModel):
    message: str
    program_name: Optional[str] = None

class GenerateRequest(BaseModel):
    program_name: str

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "rag_service"}

@app.post("/chat")
def chat_stream(req: ChatRequest):
    try:
        # 1. Qdrant'tan ilgili döküman parçalarını getir
        context = retriever.retrieve_context(req.message, req.program_name)
        
        # 2. Prompt'u oluştur
        prompt = PromptBuilder.build_chat_prompt(req.message, context)
        
        # 3. LLM'e gönder ve akış olarak döndür
        def event_generator():
            for chunk in llm.generate_stream(prompt):
                yield chunk
                
        return StreamingResponse(event_generator(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate")
def generate_report(req: GenerateRequest):
    try:
        # 1. Qdrant'tan ilgili program bilgilerini getir
        context = retriever.retrieve_context("genel bilgi başvuru şartları", req.program_name, top_k=6)
        
        # 2. Prompt'u oluştur
        prompt = PromptBuilder.build_generation_prompt(req.program_name) + f"\n\nBağlam: {context}"
        
        # 3. LLM ile yapılandırılmış JSON verisini al
        raw_response = llm.generate_complete(prompt)
        
        # Markdown kalıntılarını temizle ve JSON'a çevir
        clean_json = raw_response.replace("```json", "").replace("```", "").strip()
        veri = json.loads(clean_json)
        return veri
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rapor üretilemedi: {e}")