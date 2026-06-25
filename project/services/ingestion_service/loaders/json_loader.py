import os
import json

class JsonLoader:
    @staticmethod
    def load_json(file_name: str) -> list:
        # data/ klasörü altındaki dosyayı okur
        base_path = os.path.join(os.path.dirname(__file__), "..", "data", file_name)
        if not os.path.exists(base_path):
            raise FileNotFoundError(f"{file_name} bulunamadı: {base_path}")
            
        with open(base_path, "r", encoding="utf-8") as f:
            return json.load(f)