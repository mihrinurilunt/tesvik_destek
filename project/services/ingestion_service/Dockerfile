FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Ortak paylaşılan katmanı (shared) kopyalıyoruz
COPY shared/ ./shared

# Bağımlılıkları kopyala
COPY services/ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kod yapısını kopyala
COPY services/ingestion_service/ .

CMD ["python", "main.py"]