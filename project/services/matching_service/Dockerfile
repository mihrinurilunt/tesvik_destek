FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılıkları önce kopyala (Docker layer cache'den faydalanmak için)
COPY ./services/matching_service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY ./services/matching_service/ ./
COPY ./shared/ ./shared/

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]