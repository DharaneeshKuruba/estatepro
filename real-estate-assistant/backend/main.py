"""
FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database.init_db import init_db, seed_db
from backend.auth.routes import router as auth_router
from backend.chat.routes import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB init, seeding, and ChromaDB ingestion on startup."""
    print("[Startup] Initializing database...")
    init_db()
    seed_db()

    # Ingest documents into ChromaDB
    try:
        from backend.rag.ingestion import ingest_documents
        docs_root = os.path.join(os.path.dirname(__file__), "..", "docs")
        ingest_documents(docs_root=docs_root)
    except Exception as e:
        print(f"[Startup] ChromaDB ingestion warning: {e}")

    yield
    print("[Shutdown] Cleaning up...")


app = FastAPI(
    title="EstateNexa AI",
    description="Role-based AI assistant for real estate with RAG capabilities.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "real-estate-assistant-backend"}
