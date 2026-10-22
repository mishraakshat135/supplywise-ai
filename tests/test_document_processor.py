from pathlib import Path
import pytest
from backend.app.rag.document_processor import DocumentProcessor

SAMPLE_FILE = (Path(__file__).resolve().parents[1]/"data"/"sample_documents"/"procurement_policy.txt")

def test_load_document():
    processor = DocumentProcessor()
    documents = processor.load_document(SAMPLE_FILE)

    assert len(documents) == 1
    assert "Late Delivery Penalties" in documents[0].page_content
    assert documents[0].metadata["source"] == "procurement_policy.txt"

def test_split_documents_preserves_metadata():
    processor = DocumentProcessor(chunk_size=250, chunk_overlap=40)

    documents = processor.load_document(SAMPLE_FILE)
    chunks = processor.split_documents(documents)

    assert len(chunks)>1
    assert all(chunk.metadata["source"] == "procurement_policy.txt" for chunk in chunks)
    assert all("chunk_id" in chunk.metadata for chunk in chunks)

def test_missing_file_raises_error():
    processor = DocumentProcessor()

    with pytest.raises(FileNotFoundError):
        processor.load_document("missing_policy.txt")
        