"""
Role-aware ChromaDB retriever using PersistentClient — no separate Chroma server needed.
Filters documents by tool, user role, and agent_id.
"""
from pathlib import Path
from typing import Optional
import chromadb
from backend.core.config import get_settings

settings = get_settings()

# Resolve chroma_store path relative to this file so it works regardless of CWD
_CHROMA_PATH = str(
    (Path(__file__).parent.parent.parent / "chroma_store").resolve()
)


def _get_collection():
    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_documents(
    query: str,
    tool: Optional[str],
    user_role: str,
    agent_id: Optional[str] = None,
    n_results: int = 5,
) -> list[dict]:
    """
    Retrieve documents from ChromaDB filtered by tool and role access.
    tool=None means no tool filter (used by Summarization tool).
    """
    collection = _get_collection()

    # Build where clause — tool filter is optional
    where_conditions: list[dict] = []
    if tool:
        where_conditions.append({"tool": {"$eq": tool}})

    # Agents can only see their own documents OR documents with no agent_id
    if user_role == "agent" and agent_id:
        where_conditions.append({
            "$or": [
                {"agent_id": {"$eq": agent_id}},
                {"agent_id": {"$eq": ""}},
            ]
        })

    if len(where_conditions) > 1:
        where = {"$and": where_conditions}
    elif len(where_conditions) == 1:
        where = where_conditions[0]
    else:
        where = None

    try:
        kwargs = {
            "query_texts": [query],
            "n_results": max(n_results * 2, 10),
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)
    except Exception:
        results = collection.query(query_texts=[query], n_results=n_results * 3)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    # Post-filter: enforce role_access
    filtered: list[dict] = []
    for doc, meta in zip(documents, metadatas):
        role_access = meta.get("role_access", "")
        if user_role in role_access:
            filtered.append({"content": doc, "metadata": meta})

    return filtered[:n_results]
