"""
HTTP API client for the Streamlit frontend to communicate with the FastAPI backend.
All calls are wrapped with try/except so a slow or offline backend never crashes the page.
"""
import os
import requests
import streamlit as st
from typing import Optional

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
SHORT_TIMEOUT = 10   # auth / session reads
CHAT_TIMEOUT  = 300  # first RAG call may need model warm-up/download


def _headers() -> dict:
    token = st.session_state.get("token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _safe(resp) -> tuple[dict, int]:
    """Parse JSON safely; return error dict on failure."""
    try:
        return resp.json(), resp.status_code
    except Exception:
        return {"detail": f"Server error ({resp.status_code})."}, resp.status_code


# ── Auth ──────────────────────────────────────────────────────────────────────

def register_user(name: str, email: str, password: str) -> tuple[dict, int]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={"name": name, "email": email, "password": password, "role": "buyer"},
            timeout=SHORT_TIMEOUT,
        )
        return _safe(resp)
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot reach backend (port 8080)."}, 503
    except requests.exceptions.Timeout:
        return {"detail": "Backend timed out. Please try again."}, 504
    except Exception as e:
        return {"detail": str(e)}, 500


def login_user(email: str, password: str, role: Optional[str] = None) -> tuple[dict, int]:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": email, "password": password, "role": role},
            timeout=SHORT_TIMEOUT,
        )
        return _safe(resp)
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot reach backend (port 8080)."}, 503
    except requests.exceptions.Timeout:
        return {"detail": "Backend timed out. Please try again."}, 504
    except Exception as e:
        return {"detail": str(e)}, 500


# ── Chat ──────────────────────────────────────────────────────────────────────

def send_message(session_id: Optional[str], message: str, tool: str) -> tuple[dict, int]:
    payload: dict = {"message": message, "tool": tool}
    if session_id:
        payload["session_id"] = session_id
    try:
        resp = requests.post(
            f"{BACKEND_URL}/chat/",
            json=payload,
            headers=_headers(),
            timeout=CHAT_TIMEOUT,
        )
        return _safe(resp)
    except requests.exceptions.ConnectionError:
        return {"detail": "Cannot reach backend (port 8080)."}, 503
    except requests.exceptions.Timeout:
        return {
            "detail": (
                "Request timed out. Backend may still be warming up embeddings "
                "on first run. Please wait a bit and try again."
            )
        }, 504
    except Exception as e:
        return {"detail": str(e)}, 500


# ── Sessions / Messages ───────────────────────────────────────────────────────

def get_sessions(user_id: str) -> list:
    try:
        resp = requests.get(
            f"{BACKEND_URL}/chat/sessions/{user_id}",
            headers=_headers(),
            timeout=SHORT_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []   # silently return empty — never crash the sidebar


def get_messages(session_id: str) -> list:
    try:
        resp = requests.get(
            f"{BACKEND_URL}/chat/sessions/{session_id}/messages",
            headers=_headers(),
            timeout=SHORT_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except Exception:
        return []
