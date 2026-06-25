from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

class Embedder:
    def __init__(self):
        # OpenAI modelini yapılandırır (RAG ile aynı olmalıdır)
        self.embed_model = OpenAIEmbedding(model="text-embedding-3-small")
        Settings.embed_model = self.embed_model