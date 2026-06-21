import os
import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext, VectorStoreIndex

class QdrantUploader:
    def __init__(self):
        self.qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
        self.client = qdrant_client.QdrantClient(url=self.qdrant_url)
        self.vector_store = QdrantVectorStore(
            client=self.client, 
            collection_name="tesvikler_v2", 
            vector_name="text-dense"
        )
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def upload_nodes(self, nodes: list):
        """Metin parçalarını (nodes) indeksleyerek Qdrant'a yükler."""
        return VectorStoreIndex(nodes, storage_context=self.storage_context)