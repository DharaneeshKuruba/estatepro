"""
Role-aware ChromaDB retriever. Filters documents by tool, user role, and agent_id.
"""
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.core.config import get_settings

settings = get_settings()


def _get_collection():
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve_documents(
    query: str,
    tool: str,
    user_role: str,
    agent_id: Optional[str] = None,
    n_results: int = 5,
) -> list[dict]:
    """
    Retrieve documents from ChromaDB filtered by tool and role access.
    Post-filters results to enforce role-based access control.

    Args:
        query:      Natural-language user question.
        tool:       Tool name to filter by (e.g. 'property_retrieval').
        user_role:  User's role — 'admin', 'agent', or 'buyer'.
        agent_id:   Agent's ID string (only used when user_role == 'agent').
        n_results:  Number of chunks to return (default 5, Comparison uses 8).

    Returns:
        List of dicts with keys 'content' and 'metadata'.
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
        where = None  # no filter at all


    try:
        results = collection.query(
            query_texts=[query],
            n_results=max(n_results * 2, 10),   # over-fetch, then post-filter
            where=where,
        )
    except Exception:
        # Fallback: fetch without where and filter in Python
        results = collection.query(query_texts=[query], n_results=n_results * 3)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    # ── Post-filter: enforce role_access ──────────────────────────────────────
    filtered: list[dict] = []
    for doc, meta in zip(documents, metadatas):
        role_access = meta.get("role_access", "")
        if user_role in role_access:
            filtered.append({"content": doc, "metadata": meta})

    return filtered[:n_results]
