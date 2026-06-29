from __future__ import annotations

import json
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from shared.config import settings
from shared.enums import Language
from shared.logger import get_logger
from shared.models import Recommendation, SourceChunk

logger = get_logger(__name__)


# OpenAI'ın 'uri' format kısıtlamasını aşmak için URL'leri 'str' olan gölge modeller tanımlıyoruz
class LLMSourceChunk(BaseModel):
    chunk_id: str
    program_id: str | None = None
    program_name: str | None = None
    text: str
    score: float | None = None
    source_file: str | None = None
    source_url: str | None = None  # HttpUrl yerine str


class LLMRecommendation(BaseModel):
    program_id: str
    program_name: str
    institution: str
    score: float
    summary: str
    why_matched: list[str] = Field(default_factory=list)
    eligibility_notes: list[str] = Field(default_factory=list)
    application_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    application_url: str | None = None  # HttpUrl yerine str
    source_urls: list[str] = Field(default_factory=list)  # list[HttpUrl] yerine list[str]
    sources: list[LLMSourceChunk] = Field(default_factory=list)
    disclaimer: str = "Bu öneriler bilgilendirme amaçlıdır; resmi uygunluk veya başvuru garantisi vermez."


# OpenAI'ın parse edeceği ana taşıyıcı model gölge modelleri kullanıyor
class GenerationOutput(BaseModel):
    answer_summary: str = Field(description="Genel değerlendirme yazısı. Chat arayüzünde ilk gösterilecek metindir.")
    recommendations: list[LLMRecommendation] = Field(description="Her program için üretilmiş detaylı öneri kartları.")


class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )
        self.model = getattr(settings, "LLM_MODEL_NAME", "gpt-4o-mini")
        
        logger.info(f"LLMClient başarıyla başlatıldı. Model: {self.model}")

    async def generate_structured_recommendations(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> tuple[str, list[Recommendation]]:
        """
        Modelden şemaya tam uyumlu yapısal çıktı üretmesini talep eder.
        Dönen veriler daha sonra orijinal Recommendation modellerine doğrulanarak (validate) dönüştürülür.
        """
        try:
            # OpenAI beta Structured Outputs özelliği kullanımı (Gölge model GenerationOutput ile):
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=GenerationOutput,
                temperature=0.2
            )

            result = response.choices[0].message.parsed
            if result:
                final_recommendations: list[Recommendation] = []
                
                # LLM'den gelen gölge modelleri, orijinal projedeki pydantic modellerine dönüştürüyoruz
                for llm_rec in result.recommendations:
                    try:
                        # model_validate, string URL'leri otomatik olarak HttpUrl objelerine başarıyla dönüştürür.
                        original_rec = Recommendation.model_validate(llm_rec.model_dump(mode="json"))
                        final_recommendations.append(original_rec)
                    except Exception as val_err:
                        logger.error(f"LLM çıktısı orijinal Recommendation şemasına dönüştürülemedi: {str(val_err)}")
                
                return result.answer_summary, final_recommendations
            
            raise ValueError("LLM yapısal veriyi ayrıştıramadı.")

        except Exception as e:
            logger.error(f"Structured LLM üretimi başarısız: {str(e)}")
            return "Öneriler üretilirken teknik bir hata oluştu.", []

    async def generate_text_answer(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        """Doğal dil cevabı (/rag/answer) üretir."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Text LLM üretimi başarısız: {str(e)}")
            return "Sorunuza şu an yanıt veremiyorum, lütfen daha sonra tekrar deneyin."