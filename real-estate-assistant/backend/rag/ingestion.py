"""
ChromaDB ingestion: reads PDFs from the docs/ folder, splits them into chunks,
and upserts them with role-based access metadata.
"""
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.core.config import get_settings

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader  # fallback

settings = get_settings()

# Map filename stems → tool name
TOOL_MAP = {
    "property_documents":       "property_retrieval",
    "public_property_listings": "property_retrieval",
    "legal_documents":          "summarization",
    "market_reports":           "market_analysis",
    "market_summary":           "market_analysis",
    "investment_insights":      "investment_recommendation",
}


def _get_chroma_client():
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _read_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def _determine_metadata(file_path: Path) -> dict:
    """Derive role_access, tool, agent_id, and price_visibility from the file path."""
    fname = file_path.stem          # e.g. "property_documents_agent_AG001"
    parts = file_path.parts

    if "admin" in parts:
        role_access = ["admin"]
        agent_id = None
        price_visibility = "actual_and_quoted"
    elif "agent" in parts:
        agent_id = fname.split("_")[-1] if "_" in fname else None
        role_access = ["admin", "agent"]
        price_visibility = "actual_and_quoted"
    else:  # buyer
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
    Clear any existing collection, read all PDFs in docs_root,
    split into chunks, and upsert into ChromaDB with metadata.
    """
    docs_path = Path(docs_root)
    if not docs_path.exists():
        print(f"[Ingest] docs folder '{docs_root}' not found — skipping.")
        return 0

    client = _get_chroma_client()

    # ── Clear old chunks ───────────────────────────────────────────────────────
    try:
        client.delete_collection(name=settings.chroma_collection_name)
        print(f"[Ingest] Cleared existing collection '{settings.chroma_collection_name}'.")
    except Exception:
        pass  # Collection didn't exist yet

    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)

    pdf_files = list(docs_path.rglob("*.pdf"))
    if not pdf_files:
        print("[Ingest] No PDF files found in docs/.")
        return 0

    total_chunks = 0
    for pdf_file in pdf_files:
        try:
            content = _read_pdf(pdf_file)
        except Exception as e:
            print(f"[Ingest] WARNING: could not read {pdf_file.name}: {e}")
            continue

        if not content.strip():
            print(f"[Ingest] WARNING: {pdf_file.name} appears empty — skipping.")
            continue

        chunks = splitter.split_text(content)
        metadata = _determine_metadata(pdf_file)

        ids       = [f"{pdf_file.stem}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [metadata.copy() for _ in chunks]

        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"[Ingest] {pdf_file.name}: {len(chunks)} chunks → ChromaDB")

    print(f"[Ingest] Done. Total chunks in ChromaDB: {total_chunks}")
    return total_chunks


