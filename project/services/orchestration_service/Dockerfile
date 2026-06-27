FROM python:3.11-slim

WORKDIR /app

# Önce shared klasörünü kopyalıyoruz.
# Çünkü orchestration_service içinde shared.models, shared.schemas, shared.config import edilecek.
COPY shared /app/shared

# Orchestration servis dosyalarını kopyalıyoruz.
COPY services/orchestration_service /app/services/orchestration_service

WORKDIR /app/services/orchestration_service

RUN pip install --no-cache-dir -r requirements.txt

# /app'i Python path'e ekliyoruz ki:
# from shared.schemas import ... gibi importlar çalışsın.
ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]