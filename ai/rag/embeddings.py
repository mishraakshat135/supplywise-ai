from sentence_transformers import SentenceTransformer

class EmbeddingModel:
    def __init__(self, model_name: str="sentence-transformers/all-MiniLM-L6-v2"):
        self._model = SentenceTransformer(model_name)

    def embed_texts(self, texts):
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("Texts must not contain empty passages")

        embeddings = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy = True)

        return embeddings.tolist()

    def embed_query(self, query):
        if not query.strip():
            raise ValueError("query cannot be empty")

        embedding = self._model.encode(query, normalize_embeddings=True,convert_to_numpy=True)
        return embedding.tolist()