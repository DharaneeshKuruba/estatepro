"""
ChromaDB ingestion: reads PDFs from docs/, chunks them, and stores in ChromaDB.

Uses PersistentClient — no separate Chroma server required.
Ingestion is SKIPPED if the collection already contains data (i.e. already done before).
Pass force_reingest=True to wipe and re-ingest from scratch.
"""
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from backend.core.config import get_settings

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader  # fallback

settings = get_settings()

# Resolve chroma_store path relative to this file (not CWD dependent)
_CHROMA_PATH = str(
    (Path(__file__).parent.parent.parent / "chroma_store").resolve()
)

TOOL_MAP = {
    "property_documents":       "property_retrieval",
    "public_property_listings": "property_retrieval",
    "legal_documents":          "summarization",
    "market_reports":           "market_analysis",
    "market_summary":           "market_analysis",
    "investment_insights":      "investment_recommendation",
}


def _get_client():
    return chromadb.PersistentClient(path=_CHROMA_PATH)


def _read_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _determine_metadata(file_path: Path) -> dict:
    fname = file_path.stem
    parts = file_path.parts

    if "admin" in parts:
        role_access = ["admin"]
        agent_id = None
        price_visibility = "actual_and_quoted"
    elif "agent" in parts:
        agent_id = fname.split("_")[-1] if "_" in fname else None
        role_access = ["admin", "agent"]
        price_visibility = "actual_and_quoted"
    else:
        role_access = ["admin", "agent", "buyer"]
        agent_id = None
        price_visibility = "quoted_only"

    tool = "property_retrieval"
    for keyword, t in TOOL_MAP.items():
        if keyword in fname:
            tool = t
            break

    return {
        "tool":             tool,
        "role_access":      ",".join(role_access),
        "agent_id":         agent_id or "",
        "price_visibility": price_visibility,
        "source":           str(file_path),
    }


def ingest_documents(docs_root: str = "docs", force_reingest: bool = False):
    """
    Ingest PDFs into ChromaDB using PersistentClient.
    Skips ingestion if the collection already has data unless force_reingest=True.
    """
    client = _get_client()
    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # ── Skip if already ingested ───────────────────────────────────────────────
    existing_count = collection.count()
    if existing_count > 0 and not force_reingest:
        print(f"[Ingest] Skipping — collection already has {existing_count} chunks.")
        return existing_count

    # ── Wipe and re-ingest ─────────────────────────────────────────────────────
    if force_reingest and existing_count > 0:
        client.delete_collection(name=settings.chroma_collection_name)
        collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print("[Ingest] Cleared existing collection for re-ingestion.")

    docs_path = Path(docs_root)
    if not docs_path.exists():
        print(f"[Ingest] docs folder '{docs_root}' not found — skipping.")
        return 0

    pdf_files = list(docs_path.rglob("*.pdf"))
    if not pdf_files:
        print("[Ingest] No PDF files found.")
        return 0

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    total_chunks = 0

    for pdf_file in pdf_files:
        try:
            content = _read_pdf(pdf_file)
        except Exception as e:
            print(f"[Ingest] WARNING: could not read {pdf_file.name}: {e}")
            continue

        if not content.strip():
            print(f"[Ingest] WARNING: {pdf_file.name} is empty — skipping.")
            continue

        chunks    = splitter.split_text(content)
        metadata  = _determine_metadata(pdf_file)
        ids       = [f"{pdf_file.stem}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [metadata.copy() for _ in chunks]

        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"[Ingest] {pdf_file.name}: {len(chunks)} chunks → ChromaDB")

    print(f"[Ingest] Done. Total chunks: {total_chunks}")
    return total_chunks
