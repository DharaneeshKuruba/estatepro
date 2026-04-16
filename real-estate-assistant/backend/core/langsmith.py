"""LangSmith tracing setup helpers."""
import os
from backend.core.config import get_settings


def configure_langsmith() -> None:
    """Configure LangSmith env vars when enabled via settings/.env."""
    settings = get_settings()

    if not settings.langsmith_tracing_v2:
        print("[LangSmith] Tracing disabled.")
        return

    if not settings.langsmith_api_key:
        print("[LangSmith] Tracing enabled, but LANGSMITH_API_KEY is missing.")
        return

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith_endpoint

    print(f"[LangSmith] Tracing enabled (project={settings.langsmith_project}).")
