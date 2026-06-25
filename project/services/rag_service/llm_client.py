from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

# LLM modeli ayarları
Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0.1)

class LlmClient:
    def __init__(self):
        self.llm = Settings.llm

    def generate_stream(self, prompt: str):
        """Canlı akış (Streaming) olarak kelime kelime yanıt üretir."""
        response = self.llm.stream_complete(prompt)
        for chunk in response:
            yield chunk.delta

    def generate_complete(self, prompt: str) -> str:
        """Tek seferde tamamlanmış metin üretir."""
        response = self.llm.complete(prompt)
        return response.text