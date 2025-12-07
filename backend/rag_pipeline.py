import os
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .config import CORPUS_DIR

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

FAISS_PATH = DATA_DIR / "tfidf.index"
VECTORIZER_PATH = DATA_DIR / "tfidf_vectorizer.pkl"
CHUNKS_PATH = DATA_DIR / "tfidf_chunks.pkl"

_vectorizer = None
_faiss_index = None
_chunks: List[Document] = []


def _load_documents() -> List[Document]:
    base_path = Path(CORPUS_DIR)

    if not base_path.exists():
        raise RuntimeError(f"Corpus directory not found: {CORPUS_DIR}")

    docs = []
    txt_files = list(base_path.glob("*.txt"))

    if not txt_files:
        raise RuntimeError("No .txt files found in corpus directory")

    for file_path in txt_files:
        with file_path.open("r", encoding="utf-8") as f:
            text = f.read().strip()

        docs.append(
            Document(
                page_content=text,
                metadata={"source_file": file_path.name},
            )
        )

    return docs


def _build_vectorstore():
    global _vectorizer, _faiss_index, _chunks

    if (
        FAISS_PATH.exists()
        and VECTORIZER_PATH.exists()
        and CHUNKS_PATH.exists()
    ):
        with open(VECTORIZER_PATH, "rb") as f:
            _vectorizer = pickle.load(f)

        with open(CHUNKS_PATH, "rb") as f:
            _chunks = pickle.load(f)

        _faiss_index = faiss.read_index(str(FAISS_PATH))

        print("✅ TF-IDF RAG index loaded from disk")
        return

    print("⚠️ Building TF-IDF RAG index (first time only)...")

    documents = _load_documents()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
    )

    _chunks = splitter.split_documents(documents)
    texts = [doc.page_content for doc in _chunks]

    _vectorizer = TfidfVectorizer(stop_words="english")
    vectors = _vectorizer.fit_transform(texts).toarray().astype("float32")

    dim = vectors.shape[1]
    _faiss_index = faiss.IndexFlatL2(dim)
    _faiss_index.add(vectors)

    faiss.write_index(_faiss_index, str(FAISS_PATH))

    with open(VECTORIZER_PATH, "wb") as f:
        pickle.dump(_vectorizer, f)

    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(_chunks, f)

    print("✅ TF-IDF RAG index built & saved")


def retrieve_context(question: str, k: int = 4) -> Tuple[str, List[Document]]:
    _build_vectorstore()

    query_vec = _vectorizer.transform([question]).toarray().astype("float32")

    D, I = _faiss_index.search(query_vec, k)

    docs = [_chunks[i] for i in I[0] if i < len(_chunks)]

    combined_text = "\n\n".join(doc.page_content for doc in docs)

    return combined_text, docs
