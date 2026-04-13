"""
ChromaDB ingestion: loads generated documents from disk, splits them into chunks,
and upserts them with role-based access metadata.
"""
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.core.config import get_settings
from backend.rag.document_generator import write_documents, PROPERTY_DOCS

settings = get_settings()

# Tool mapping by keyword in filename / content category
TOOL_MAP = {
    "property_documents": "property_retrieval",
    "public_property_listings": "property_retrieval",
    "legal_documents": "summarization",
    "market_reports": "market_analysis",
    "market_summary": "market_analysis",
    "investment_insights": "investment_recommendation",
}


def _get_chroma_client():
    return chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def _determine_metadata(file_path: str) -> dict:
    """Derive role_access, tool, agent_id, and price_visibility from the file path."""
    fname = Path(file_path).stem  # e.g. "property_documents_agent_AG001"
    parts = Path(file_path).parts

    # Determine role access from folder
    if "admin" in parts:
        role_access = ["admin"]
        agent_id = None
        price_visibility = "actual_and_quoted"
    elif "agent" in parts:
        # e.g. property_documents_agent_AG001 → extract AG001
        agent_id = fname.split("_")[-1] if "_" in fname else None
        role_access = ["admin", "agent"]
        price_visibility = "actual_and_quoted"
    else:  # buyer
        role_access = ["admin", "agent", "buyer"]
        agent_id = None
        price_visibility = "quoted_only"

    # Determine tool
    tool = "property_retrieval"
    for keyword, t in TOOL_MAP.items():
        if keyword in fname:
            tool = t
            break

    return {
        "tool": tool,
        "role_access": ",".join(role_access),  # Chroma metadata must be scalar or list of scalars
        "agent_id": agent_id or "",
        "price_visibility": price_visibility,
        "source": str(file_path),
    }


def ingest_documents(docs_root: str = "docs", force_reingest: bool = False):
    """
    Generate documents if they don't exist, split them into chunks,
    and upsert into ChromaDB with metadata.
    """
    # Generate / ensure docs exist
    docs_path = Path(docs_root)
    if not docs_path.exists() or force_reingest:
        write_documents(docs_root)

    client = _get_chroma_client()
    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)

    all_txt_files = list(docs_path.rglob("*.txt"))
    total_chunks = 0

    for txt_file in all_txt_files:
        content = txt_file.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)
        metadata = _determine_metadata(str(txt_file))

        ids = [f"{txt_file.stem}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [metadata.copy() for _ in chunks]

        # Also store per-property agent_id for agent-specific queries on combined docs
        if "all" in txt_file.stem:
            # For the all-properties doc, split by agent and tag each chunk
            for j, (chunk_text, chunk_id, chunk_meta) in enumerate(zip(chunks, ids, metadatas)):
                for agent_id in PROPERTY_DOCS:
                    if agent_id in chunk_text:
                        chunk_meta["agent_id"] = agent_id
                        break

        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"[Ingest] {txt_file.name}: {len(chunks)} chunks → ChromaDB")

    print(f"[Ingest] Done. Total chunks in ChromaDB: {total_chunks}")
    return total_chunks
