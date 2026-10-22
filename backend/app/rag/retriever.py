from pathlib import Path
from typing import Any
import chromadb
from langchain_core.documents import Document
from backend.app.rag.embeddings import EmbeddingModel

class RAGRetriever:
    def __init__(self, embedding_model: EmbeddingModel, persist_directory: str|Path="./chroma_db", collection_name: str="supplywise_procurement"):
        self._embedding_model = embedding_model
        persist_path = Path(persist_directory).resolve()
        persist_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_path))
        self._collection = self._client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    def add_documents(self, documents):
        if not documents: 
            return 0

        ids: list[str] = []
        texts: list[str] = []
        metadatas : list[dict[str, Any]] = []

        for index, document in enumerate(documents):
            source = str(document.metadata.get("source", "unknown"))
            chunk_id = str(document.metadata.get("chunk_id", index))
            ids.append(f"{source}:{chunk_id}")
            texts.append(document.page_content)
            metadatas.append(
                {
                    key: value
                    for key, value in document.metadata.items()
                    if isinstance(value, (str, int, float, bool))
                }
            )

        embeddings = self._embedding_model.embed_texts(texts)

        self._collection.upsert(
            ids=ids,
            documents = texts,
            embeddings = embeddings,
            metadatas = metadatas
        )
        return len(ids)

    def search(self, query, k: int=3):
        if not query.strip():
            raise ValueError("query can not be empty")
        if k <=0:
            raise ValueError("k must be positive")
        if self._collection.count() == 0:
            return []

        query_embedding = self._embedding_model.embed_query(query)
        result= self._collection.query(
            query_embeddings = [query_embedding],
            n_results = min(k, self._collection.count()),
            include = ["documents", "metadatas", "distances"]
        )

        documents: list[Document] = []
        result_texts = result["documents"]
        result_metadatas = result["metadatas"]
        result_distances = result["distances"]

        if not result_texts or result_texts[0] is None:
            return []

        for text, metadata, distance in zip(result_texts[0], result_metadatas[0], result_distances[0]):
            documents.append(Document(
                page_content = text,
                metadata={
                    **(metadata or {}),
                    "distance": distance
                },
            ))
        return documents