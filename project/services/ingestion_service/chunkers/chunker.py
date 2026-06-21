from llama_index.core.node_parser import SentenceSplitter

class Chunker:
    @staticmethod
    def split_text(documents: list, chunk_size: int = 500, chunk_overlap: int = 50) -> list:
        # Llama-index splitter kullanarak dökümanları anlamlı parçalara böler
        splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return splitter.get_nodes_from_documents(documents)