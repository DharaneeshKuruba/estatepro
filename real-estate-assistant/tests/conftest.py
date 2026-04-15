import os
import sys
import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable for backend.* modules.
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Test-safe defaults
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("GROQ_MODEL", "test-model")
os.environ.setdefault("CHROMA_HOST", "localhost")
os.environ.setdefault("CHROMA_PORT", "9999")

from backend.core.security import create_access_token, hash_password
from backend.database.models import ChatSession, Message, User


EMAIL_BY_ROLE = {
    "admin": "admin@realestate.com",
    "agent": "agent1@realestate.com",
    "buyer": "buyer@test.com",
}
NAME_BY_ROLE = {
    "admin": "System Admin",
    "agent": "Agent One",
    "buyer": "Test Buyer",
}


def _make_user(role: str, email: Optional[str] = None, agent_id: Optional[str] = None) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.name = NAME_BY_ROLE.get(role, f"{role.title()} User")
    user.email = email or EMAIL_BY_ROLE.get(role, f"{role}@test.com")
    user.password_hash = hash_password("TestPassword@1")
    user.role = role
    user.agent_id = agent_id
    user.created_at = datetime.utcnow()
    return user


def _extract_binary_value(expr):
    left_name = getattr(getattr(expr, "left", None), "name", None)
    right = getattr(expr, "right", None)
    if right is None:
        return left_name, None

    if hasattr(right, "value"):
        return left_name, right.value
    if hasattr(right, "effective_value"):
        return left_name, right.effective_value
    return left_name, None


@pytest.fixture(scope="module")
def client():
    from backend.database.session import get_db
    from backend.main import app

    users_by_email: dict[str, User] = {}
    sessions_by_id: dict[str, ChatSession] = {}
    messages_by_session: dict[str, list[Message]] = {}

    admin_user = _make_user("admin")
    agent_user = _make_user("agent", agent_id="AG001")
    buyer_user = _make_user("buyer")

    users_by_email[admin_user.email] = admin_user
    users_by_email[agent_user.email] = agent_user
    users_by_email[buyer_user.email] = buyer_user

    def seed_user(role: str, email: str, password: str = "TestPassword@1", agent_id: Optional[str] = None) -> User:
        user = _make_user(role=role, email=email, agent_id=agent_id)
        user.password_hash = hash_password(password)
        users_by_email[email] = user
        return user

    class _QueryProxy:
        def __init__(self, model):
            self._model = model
            self._filters = []

        def filter(self, *args, **kwargs):
            self._filters.extend(args)
            return self

        def filter_by(self, **kwargs):
            return self

        def _filtered_users(self):
            data = list(users_by_email.values())
            for expr in self._filters:
                name, val = _extract_binary_value(expr)
                if name == "email" and val is not None:
                    data = [u for u in data if u.email == str(val)]
                elif name == "role" and val is not None:
                    data = [u for u in data if u.role == str(val)]
                elif name == "id" and val is not None:
                    data = [u for u in data if str(u.id) == str(val)]
            return data

        def _filtered_sessions(self):
            data = list(sessions_by_id.values())
            for expr in self._filters:
                name, val = _extract_binary_value(expr)
                if name == "id" and val is not None:
                    data = [s for s in data if str(s.id) == str(val)]
                elif name == "user_id" and val is not None:
                    data = [s for s in data if str(s.user_id) == str(val)]
            return data

        def _filtered_messages(self):
            session_id = None
            for expr in self._filters:
                name, val = _extract_binary_value(expr)
                if name == "session_id" and val is not None:
                    session_id = str(val)
            if not session_id:
                return []
            return list(messages_by_session.get(session_id, []))

        def first(self):
            if self._model is User:
                users = self._filtered_users()
                return users[0] if users else None
            if self._model is ChatSession:
                sessions = self._filtered_sessions()
                return sessions[0] if sessions else None
            if self._model is Message:
                messages = self._filtered_messages()
                return messages[0] if messages else None
            return None

        def count(self):
            if self._model is User:
                return len(self._filtered_users())
            if self._model is ChatSession:
                return len(self._filtered_sessions())
            if self._model is Message:
                return len(self._filtered_messages())
            return 0

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            if self._model is User:
                return self._filtered_users()
            if self._model is ChatSession:
                return self._filtered_sessions()
            if self._model is Message:
                return self._filtered_messages()
            return []

    mock_db = MagicMock()

    def _add(obj):
        if isinstance(obj, User):
            users_by_email[obj.email] = obj
            if not getattr(obj, "created_at", None):
                obj.created_at = datetime.utcnow()
        elif isinstance(obj, ChatSession):
            sessions_by_id[str(obj.id)] = obj
            if not getattr(obj, "created_at", None):
                obj.created_at = datetime.utcnow()
        elif isinstance(obj, Message):
            sid = str(obj.session_id)
            messages_by_session.setdefault(sid, []).append(obj)
            if not getattr(obj, "created_at", None):
                obj.created_at = datetime.utcnow()

    def _refresh(obj):
        return None

    mock_db.query = lambda model: _QueryProxy(model)
    mock_db.add = _add
    mock_db.commit = MagicMock()
    mock_db.refresh = _refresh
    mock_db.close = MagicMock()

    def override_db():
        yield mock_db

    def make_token(role: str, email: Optional[str] = None, agent_id: Optional[str] = None) -> str:
        token_email = email or EMAIL_BY_ROLE[role]
        token_agent_id = agent_id if agent_id is not None else ("AG001" if role == "agent" else None)
        return create_access_token({"sub": token_email, "role": role, "agent_id": token_agent_id})

    def make_headers(role: str, email: Optional[str] = None, agent_id: Optional[str] = None) -> dict:
        return {"Authorization": f"Bearer {make_token(role=role, email=email, agent_id=agent_id)}"}

    app.dependency_overrides[get_db] = override_db

    with patch("backend.chat.routes.run_tool", side_effect=lambda tool, query, user_role, agent_id=None: f"Mocked response: {tool} [{user_role}]"), \
         patch("backend.rag.ingestion.ingest_documents", return_value=0), \
         patch("backend.main.init_db", return_value=None), \
         patch("backend.main.seed_db", return_value=None):
        with TestClient(app, raise_server_exceptions=False) as test_client:
            test_client._users = users_by_email
            test_client._sessions = sessions_by_id
            test_client._messages = messages_by_session
            test_client._admin_user = admin_user
            test_client._agent_user = agent_user
            test_client._buyer_user = buyer_user
            test_client.make_token = make_token
            test_client.make_headers = make_headers
            test_client.seed_user = seed_user
            yield test_client

    app.dependency_overrides.clear()
