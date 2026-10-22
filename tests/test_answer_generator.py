from unittest.mock import Mock
import pytest
from langchain_core.documents import Document
from backend.app.rag.answer_generator import RAGAnswerGenerator


def make_generator():
    generator = RAGAnswerGenerator.__new__(RAGAnswerGenerator)
    generator._llm = Mock()
    return generator


def test_empty_query_is_rejected():
    generator = make_generator()

    with pytest.raises(ValueError, match="Query cannot be empty"):
        generator.generate_answer("   ", [])


def test_no_documents_returns_insufficient_evidence():
    generator = make_generator()

    result = generator.generate_answer(
        "What is the late delivery penalty?", []
    )

    assert "could not find relevant evidence" in result["answer"].lower()
    assert result["sources"] == {}
    generator._llm.invoke.assert_not_called()


def test_answer_returns_valid_source_mapping():
    generator = make_generator()
    generator._llm.invoke.return_value = Mock(
        content="The penalty may be 2% of the delayed order value [S1]."
    )

    documents = [
        Document(
            page_content="A 2% penalty may apply under the signed contract.",
            metadata={"source": "procurement_policy.txt", "chunk_id": 2},
        )
    ]

    result = generator.generate_answer(
        "What is the late delivery penalty?", documents
    )

    assert "[S1]" in result["answer"]
    assert "S1" in result["sources"]
    assert (
        result["sources"]["S1"]["source"]
        == "procurement_policy.txt"
    )


def test_invalid_citation_is_removed():
    generator = make_generator()
    generator._llm.invoke.return_value = Mock(
        content="The policy requires approval [S1]. Another rule says [S9]."
    )

    documents = [
        Document(
            page_content="Orders above ₹100,000 need approval.",
            metadata={"source": "procurement_policy.txt"},
        )
    ]

    result = generator.generate_answer("Approval threshold?", documents)

    assert "[S1]" in result["answer"]
    assert "[S9]" not in result["answer"]
    assert set(result["sources"]) == {"S1"}


def test_llm_exception_returns_controlled_error():
    generator = make_generator()
    generator._llm = Mock()
    generator._llm.invoke.side_effect = RuntimeError(
        "Simulated provider failure"
    )

    result = generator.generate_answer(
        "What is the late delivery penalty?",
        [
            Document(
                page_content="A penalty of 2% may apply after a delay exceeding 7 days.",
                metadata={"source": "procurement_policy.txt", "chunk_id": 0},
            )
        ],
    )

    assert result["status"] == "error"
    assert result["error_type"] == "RuntimeError"
    assert result["sources"] == {}
    assert "failed" in result["answer"].lower()


def test_empty_llm_response_returns_controlled_error():
    generator = make_generator()
    generator._llm = Mock()
    generator._llm.invoke.return_value = Mock(content="")

    result = generator.generate_answer(
        "What is the late delivery penalty?",
        [
            Document(
                page_content="A penalty of 2% may apply after a delay exceeding 7 days.",
                metadata={"source": "procurement_policy.txt", "chunk_id": 0},
            )
        ],
    )

    assert result["status"] == "error"
    assert result["error_type"] == "EmptyModelResponse"
    assert result["sources"] == {}
    assert "no usable text" in result["answer"].lower()

