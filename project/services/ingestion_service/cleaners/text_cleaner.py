import re

class TextCleaner:
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        # Gereksiz HTML etiketlerini ve çoklu boşlukları temizler
        text = re.sub(r'<[^>]*>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()