
from pathlib import Path
from typing import Any
from backend.app.agents.base_agent import BaseAgent
from backend.app.rag.document_processor import DocumentProcessor
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.answer_generator import RAGAnswerGenerator

class PolicyAnalystAgent(BaseAgent):
    """to analyze procurement policies using rag"""

    def __init__(self, policy_directory: str | Path | None = None, persist_directory: str | Path | None = None):
        super().__init__("PolicyAnalystAgent")

        project_root = Path(__file__).resolve().parents[3]

        self._policy_directory = (Path(policy_directory) if policy_directory is not None else project_root / "data" / "sample_documents")

        chroma_directory = (Path(persist_directory) if persist_directory is not None else project_root / "chroma_db")

        if not self._policy_directory.is_dir():
            raise FileNotFoundError(
                f"Can not find policy directory: {self._policy_directory}"
            )

        self._document_processor = DocumentProcessor()
        self._embedding_model = EmbeddingModel()

        self._retriever = RAGRetriever(
            embedding_model=self._embedding_model,
            persist_directory=chroma_directory,
            collection_name="supplywise_policy",
        )

        self._answer_generator = RAGAnswerGenerator()
        self._index_policy_documents()

    def _index_policy_documents(self):
        """load and index all supported policy files"""
        files = sorted(path for path in self._policy_directory.rglob("*") if path.is_file() and path.suffix.lower() in DocumentProcessor.SUPPORTED_EXTENSIONS )

        if not files:
            raise FileNotFoundError(f"No supported PDF or TXT policy files found in {self._policy_directory}")

        total_chunks = 0

        for file_path in files:
            chunks = self._document_processor.process_file(file_path)
            relative_source = file_path.relative_to(self._policy_directory).as_posix()

            for chunk in chunks:
                chunk.metadata["source"] = relative_source

            total_chunks += self._retriever.add_documents(chunks)

        return total_chunks

    def run(self, context):
        query = context.get("query", "")

        if not isinstance(query, str) or not query.strip():
            return {
                "agent": self.name,
                "status": "error",
                "error": "A non-empty query is needed",
            }

        try:
            retrieved_documents = self._retriever.search(query, k=3)

            if not retrieved_documents:
                return {
                    "agent": self.name,
                    "status": "success",
                    "query": query,
                    "answer": ("I could not find relevant evidence in the available documents."),
                    "sources": {},
                }

            result = self._answer_generator.generate_answer(query, retrieved_documents)

            if result.get("status") == "error":
                return {
                    "agent": self.name,
                    "status": "error",
                    "query": query,
                    "error": (f"Policy answer generation failed: {result.get('error_type', 'UnknownError')}"),
                    "answer": result.get("answer"),
                    "sources": {},
                }

            return {
                "agent": self.name,
                "status": "success",
                "query": query,
                "answer": result["answer"],
                "sources": result["sources"],
            }

        except Exception as exc:
            return {
                "agent": self.name,
                "status": "error",
                "query": query,
                "error": f"Policy analysis failed: {type(exc).__name__}",
            }
