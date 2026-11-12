from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentProcessor:
    SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

    def __init__(self, chunk_size: int=800, chunk_overlap: int=120):

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non negative and smaller than chunk_size")

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap,
            add_start_index = True
        )

    def load_document(self, file_path):
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"document not found: {path}")

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"unsupported file type: {extension}\nonly pdf and txt are supported")

        if extension == ".pdf":
            loaded_document = PyPDFLoader(str(path).load())
        else:
            loaded_documents = TextLoader(str(path), encoding="utf-8").load()

        for document in loaded_documents: 
            document.metadata["source"] = path.name

        return loaded_documents

    def split_documents(self, documents):
        if not documents:
            return []

        chunks = self._splitter.split_documents(documents)

        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = index

        return chunks

    def process_file(self, file_path):
        documents = self.load_document(file_path)
        return self.split_documents(documents)