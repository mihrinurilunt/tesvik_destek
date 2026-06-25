import os
import qdrant_client
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

# Embedding modeli ayarları
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# Docker ağında veya lokalde Qdrant bağlantı adresi
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")

class RagRetriever:
    def __init__(self):
        self.client = qdrant_client.QdrantClient(url=QDRANT_URL)
        self.vector_store = QdrantVectorStore(client=self.client, collection_name="tesvikler_v2", vector_name="text-dense")
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.index = VectorStoreIndex.from_vector_store(self.vector_store, storage_context=self.storage_context)

# services/rag_service/retrieval.py dosyasındaki fonksiyonun güncel hali:

    def retrieve_context(self, query: str, program_name: str = None, top_k: int = 4) -> str:
        """
        Qdrant üzerinden ilgili döküman parçalarını (nodes/chunks) getirir.
        Program adı belirtilmemişse genel veritabanı araması (filtresiz) yapar.
        """
        filtreler = None
        
        # Akıllı Filtre Kontrolü: 
        # program_name None değilse, boş değilse ve Swagger'ın varsayılan "string" kelimesi değilse filtre uygula
# services/rag_service/retrieval.py içindeki ilgili kısmı şu şekilde güncelleyin:

        if program_name and program_name.strip() and program_name.lower() != "string":
            filtreler = MetadataFilters(
                # "program_adi" yerine "program_name" yapıyoruz (API Contract Uyumu)
                filters=[MetadataFilter(key="program_name", value=program_name.strip())]
            )
            print(f"🎯 RAG araması '{program_name}' programı için filtrelendi.")
        else:
            # Filtre None kalırsa Qdrant tüm koleksiyonda semantik arama yapar!
            print("🌐 RAG araması genel veritabanı genelinde (filtresiz) yapılıyor.")
            
        retriever = self.index.as_retriever(similarity_top_k=top_k, filters=filtreler)
        nodes = retriever.retrieve(query)
        
        context_text = "\n\n".join([node.node.get_content() for node in nodes])
        return context_text