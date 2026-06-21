FROM python:3.11-slim

WORKDIR /app

# Dosyaları project/ ana klasöründen yollarıyla birlikte kopyalıyoruz
COPY services/ingestion_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ingestion_service/main.py .
COPY services/ingestion_service/yeni_destekler.json .

CMD ["python", "main.py"]