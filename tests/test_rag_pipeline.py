from pathlib import Path
from backend.app.rag.document_processor import DocumentProcessor
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.rag.retriever import RAGRetriever
from backend.app.rag.answer_generator import RAGAnswerGenerator

def test_procurement_policy_rag_pipeline(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    policy_path = (project_root/"data"/"sample_documents"/"procurement_policy.txt")

    assert policy_path.exists(), f"Policy not found: {policy_path}"

    processor = DocumentProcessor(
        chunk_size=250,
        chunk_overlap=40,
    )
    chunks = processor.process_file(policy_path)

    assert chunks, "The document processor returned no chunks."

    embedding_model = EmbeddingModel()

    retriever = RAGRetriever(
        embedding_model=embedding_model,
        persist_directory=tmp_path / "chroma_db",
        collection_name="pipeline_test",
    )

    stored_count = retriever.add_documents(chunks)
    assert stored_count == len(chunks)

    query = "What penalty may apply for late delivery?"
    retrieved_documents = retriever.search(query, k=3)

    assert retrieved_documents, "No relevant policy passages retrieved."

    generator = RAGAnswerGenerator()
    result = generator.generate_answer(query, retrieved_documents)
    assert result["answer"].strip(), "The generated answer is empty."
    assert isinstance(result["sources"], dict)

    print("\nGenerated answer:")
    print(result["answer"])

    print("\nSources:")
    for source_id, source_info in result["sources"].items():
        print(f"[{source_id}] {source_info}")
