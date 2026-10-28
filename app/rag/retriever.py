"""Retrieval layer.

ABSTRACTION: DocumentRetriever hides HOW we search.
POLYMORPHISM: KeywordRetriever (no dependencies, works out of the box) and
ChromaRetriever (real embeddings) are interchangeable - switch with RETRIEVER_BACKEND.
"""
from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, asdict

from app.rag.chunker import chunk_text


@dataclass
class RetrievedChunk:
    doc_id: int
    filename: str
    chunk_index: int
    text: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


class DocumentRetriever(ABC):
    @abstractmethod
    def index_document(self, doc_id: int, filename: str, text: str) -> int:
        """Chunk + index a document. Returns number of chunks. (No LLM retraining needed.)"""

    @abstractmethod
    def remove_document(self, doc_id: int) -> None: ...

    @abstractmethod
    def search(self, query: str, k: int = 4) -> list[RetrievedChunk]: ...


_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "is", "are", "be", "with",
         "by", "at", "as", "that", "this", "it", "from", "will", "shall", "must", "any"}


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class KeywordRetriever(DocumentRetriever):
    """BM25-style keyword search kept in memory. Index is rebuilt from the DB at startup."""

    def __init__(self):
        self._chunks: list[tuple[int, str, int, str, Counter]] = []

    def index_document(self, doc_id, filename, text):
        self.remove_document(doc_id)
        pieces = chunk_text(text)
        for i, piece in enumerate(pieces):
            self._chunks.append((doc_id, filename, i, piece, Counter(_tokens(piece))))
        return len(pieces)

    def remove_document(self, doc_id):
        self._chunks = [c for c in self._chunks if c[0] != doc_id]

    def search(self, query, k=4):
        q = _tokens(query)
        if not q or not self._chunks:
            return []
        n = len(self._chunks)
        avg_len = sum(sum(c[4].values()) for c in self._chunks) / n or 1
        df = Counter(t for c in self._chunks for t in set(c[4]))
        results = []
        for doc_id, fname, idx, text, tf in self._chunks:
            dl = sum(tf.values()) or 1
            score = 0.0
            for t in set(q):
                if t in tf:
                    idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                    score += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * dl / avg_len))
            if score > 0:
                results.append(RetrievedChunk(doc_id, fname, idx, text, round(score, 4)))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:k]


class ChromaRetriever(DocumentRetriever):
    """Embedding-based retrieval with ChromaDB + Sentence Transformers.

    TODO(INTEGRATION: RAG): This is the real vector-search version. To enable:
        pip install chromadb sentence-transformers
        .env -> RETRIEVER_BACKEND=chroma
    The RAG member can tune: embedding model, chunk size, top-k, metadata filters
    (e.g. only search `doc_type == "contract"`), re-ranking, FAISS instead of Chroma.
    Only this class needs to change - agents/routes use the DocumentRetriever interface.
    """

    def __init__(self, persist_dir: str, embedding_model: str):
        import chromadb  # lazy imports: only needed when this backend is selected
        from sentence_transformers import SentenceTransformer

        self._embedder = SentenceTransformer(embedding_model)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._col = self._client.get_or_create_collection("supplywise_docs",
                                                          metadata={"hnsw:space": "cosine"})

    def index_document(self, doc_id, filename, text):
        self.remove_document(doc_id)
        pieces = chunk_text(text)
        if not pieces:
            return 0
        embeddings = self._embedder.encode(pieces).tolist()
        self._col.add(
            ids=[f"{doc_id}:{i}" for i in range(len(pieces))],
            documents=pieces, embeddings=embeddings,
            metadatas=[{"doc_id": doc_id, "filename": filename, "chunk_index": i} for i in range(len(pieces))],
        )
        return len(pieces)

    def remove_document(self, doc_id):
        self._col.delete(where={"doc_id": doc_id})

    def search(self, query, k=4):
        emb = self._embedder.encode([query]).tolist()
        res = self._col.query(query_embeddings=emb, n_results=k)
        out = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            out.append(RetrievedChunk(meta["doc_id"], meta["filename"], meta["chunk_index"],
                                      text, round(1 - float(dist), 4)))
        return out
