FROM python:3.11-slim

WORKDIR /app

# shared klasörünü root context'ten kopyala
COPY shared/ ./shared/

# servis dosyalarını kopyala
COPY services/matching_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/matching_service/ .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]