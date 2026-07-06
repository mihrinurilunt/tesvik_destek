from llama_index.core.node_parser import SentenceSplitter

    # ingestion_service/chunkers/chunker.py
class Chunker:
    @staticmethod
    def split_text(documents: list, chunk_size: int = 1024, chunk_overlap: int = 128) -> list:
        splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return splitter.get_nodes_from_documents(documents)