from pathlib import Path
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# =========================
# ✅ CORRECTED PATHS
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CORPUS_DIR = PROJECT_ROOT / "data" / "corpus"
VECTOR_DIR = PROJECT_ROOT / "backend" / "vector_store"

VECTOR_DIR.mkdir(parents=True, exist_ok=True)

print("📂 CORPUS DIRECTORY:", CORPUS_DIR)
print("📂 VECTOR STORE DIRECTORY:", VECTOR_DIR)

# =========================
# ✅ EMBEDDINGS
# =========================
embeddings = OllamaEmbeddings(model="mistral")

# =========================
# ✅ TEXT SPLITTER
# =========================
splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
)

# =========================
# ✅ LOAD DOCUMENTS
# =========================
def load_documents():
    if not CORPUS_DIR.exists():
        raise RuntimeError(f"❌ Corpus directory not found: {CORPUS_DIR}")

    files = list(CORPUS_DIR.glob("*.txt"))
    if not files:
        raise RuntimeError(f"❌ No .txt files found in: {CORPUS_DIR}")

    documents = []

    for file in files:
        text = file.read_text(encoding="utf-8", errors="ignore").strip()
        chunks = splitter.split_text(text)

        for i, chunk in enumerate(chunks):
            documents.append(
                Document(
                    page_content=chunk,
                    metadata={
                        "source": file.name,
                        "chunk": i,
                    },
                )
            )

    print(f"✅ Loaded {len(documents)} chunks from {len(files)} files")
    return documents


# =========================
# ✅ BUILD FAISS INDEX
# =========================
def build_faiss():
    docs = load_documents()

    print("⚡ Creating embeddings...")
    db = FAISS.from_documents(docs, embeddings)

    db.save_local(VECTOR_DIR)

    print("✅ FAISS INDEX BUILT SUCCESSFULLY")
    print("📁 Files created:")
    print("   - index.faiss")
    print("   - index.pkl")


# =========================
# ✅ RUN
# =========================
if __name__ == "__main__":
    print("🔄 Building FAISS index from corpus...")
    build_faiss()
