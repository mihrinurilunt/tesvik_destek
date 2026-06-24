FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Ortak paylaşılan katmanı (shared) kopyalıyoruz (Çok Önemli)
COPY shared/ ./shared

# Servisin kendi bağımlılıklarını kopyala
COPY services/rag_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# rag_service kodlarını kopyala
COPY services/rag_service/main.py .
COPY services/rag_service/retrieval.py .
COPY services/rag_service/prompt_builder.py .
COPY services/rag_service/llm_client.py .

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]