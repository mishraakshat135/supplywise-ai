from pathlib import Path
import pytest
from backend.app.rag.document_processor import DocumentProcessor
from backend.app.rag.embeddings import EmbeddingModel
from backend.app.rag.retriever import RAGRetriever


@pytest.fixture(scope="module")
def indexed_policy(tmp_path_factory):
    policy_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "sample_documents"
        / "procurement_policy.txt"
    )

    processor = DocumentProcessor(
        chunk_size=250,
        chunk_overlap=40,
    )
    chunks = processor.process_file(policy_path)

    model = EmbeddingModel()
    retriever = RAGRetriever(
        embedding_model=model,
        persist_directory=tmp_path_factory.mktemp("chroma_db"),
        collection_name="test_procurement_policy",
    )

    stored_count = retriever.add_documents(chunks)

    assert stored_count == len(chunks)

    return retriever


@pytest.mark.parametrize(
    ("query", "expected_terms"),
    [
        (
            "What is the penalty for a very late delivery?",
            ["2%", "penalty"],
        ),
        (
            "How many days are allowed for standard purchase orders?",
            ["7 calendar days", "delivery"],
        ),
        (
            "What is the supplier's minimum order quantity rule?",
            ["minimum order quantity", "MOQ"],
        ),
        (
            "Who must approve a purchase order exceeding ₹100,000?",
            ["100,000", "approval"],
        ),
        (
            "Can we select a supplier based only on the lowest price?",
            ["price", "reliability"],
        ),
    ],
)
def test_retriever_finds_relevant_policy(
    indexed_policy,
    query,
    expected_terms,
):
    results = indexed_policy.search(query, k=3)

    assert results, f"No policy passages retrieved for: {query}"

    retrieved_text = "\n".join(
        document.page_content.lower()
        for document in results
    )

    assert any(
        term.lower() in retrieved_text
        for term in expected_terms
    ), (
        f"Expected at least one of {expected_terms} in the "
        f"retrieved passages for query: {query}"
    )

    assert all(
        document.metadata.get("source") == "procurement_policy.txt"
        for document in results
    )


def test_retrieval_is_repeatable(indexed_policy):
    query = "What penalty applies to late delivery?"

    first_results = indexed_policy.search(query, k=3)
    second_results = indexed_policy.search(query, k=3)

    assert first_results
    assert second_results

    assert [
        document.page_content for document in first_results
    ] == [
        document.page_content for document in second_results
    ]


def test_empty_query_is_rejected(indexed_policy):
    with pytest.raises(ValueError):
        indexed_policy.search("   ", k=3)
