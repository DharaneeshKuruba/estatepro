import uuid

import pytest

TOOL_NAME = "comparison"

ROLE_CONFIG = [
    ("admin", None),
    ("agent", "AG001"),
    ("buyer", None),
]

DIRECT_MESSAGES = [
    "Show listings in Bangalore",
    "2bhk near metro",
    "budget under 1cr",
    "Find options with parking",
    "Compare east-facing units",
    "Need gated community",
    "Tell me about schools nearby",
    "Is this area flood safe",
    "show me roi potential",
    "family-friendly neighborhood",
    "single line",
    '{"query": "structured"}',
    "'; DROP TABLE users; --",
    "<script>alert('xss')</script>",
    " ",
]

FOLLOW_UP_MESSAGES = [
    "Can you expand on that",
    "Give pros and cons",
    "Add pricing context",
    "What is the downside",
    "Summarize in bullets",
]

DIRECT_CASES = []
for role, agent_id in ROLE_CONFIG:
    for idx, message in enumerate(DIRECT_MESSAGES, start=1):
        DIRECT_CASES.append(
            {
                "id": f"{TOOL_NAME}-{role}-direct-{idx}",
                "kind": "direct",
                "role": role,
                "agent_id": agent_id,
                "message": message,
                "expected": 200,
            }
        )

FOLLOW_UP_CASES = []
for role, agent_id in ROLE_CONFIG:
    for idx, message in enumerate(FOLLOW_UP_MESSAGES, start=1):
        FOLLOW_UP_CASES.append(
            {
                "id": f"{TOOL_NAME}-{role}-followup-{idx}",
                "kind": "follow_up",
                "role": role,
                "agent_id": agent_id,
                "message": message,
                "expected": 200,
            }
        )

NEGATIVE_CASES = [
    {"id": f"{TOOL_NAME}-unauthenticated", "kind": "unauthenticated", "expected": 401},
    {"id": f"{TOOL_NAME}-invalid-token", "kind": "invalid_token", "expected": 401},
    {"id": f"{TOOL_NAME}-wrong-auth-scheme", "kind": "wrong_auth_scheme", "expected": 401},
    {
        "id": f"{TOOL_NAME}-missing-message-admin",
        "kind": "raw_payload",
        "role": "admin",
        "payload": {"tool": TOOL_NAME},
        "expected": 422,
    },
    {
        "id": f"{TOOL_NAME}-null-message-agent",
        "kind": "raw_payload",
        "role": "agent",
        "agent_id": "AG001",
        "payload": {"tool": TOOL_NAME, "message": None},
        "expected": 422,
    },
    {
        "id": f"{TOOL_NAME}-empty-body-buyer",
        "kind": "raw_payload",
        "role": "buyer",
        "payload": {},
        "expected": 422,
    },
    {
        "id": f"{TOOL_NAME}-random-session-admin",
        "kind": "random_session",
        "role": "admin",
        "expected": 404,
    },
    {
        "id": f"{TOOL_NAME}-random-session-agent",
        "kind": "random_session",
        "role": "agent",
        "agent_id": "AG001",
        "expected": 404,
    },
    {
        "id": f"{TOOL_NAME}-random-session-buyer",
        "kind": "random_session",
        "role": "buyer",
        "expected": 404,
    },
    {
        "id": f"{TOOL_NAME}-cross-owner-session",
        "kind": "cross_owner_session",
        "owner_role": "admin",
        "requester_role": "buyer",
        "expected": 404,
    },
]

ALL_CASES = DIRECT_CASES + FOLLOW_UP_CASES + NEGATIVE_CASES
assert len(ALL_CASES) == 70


def _post_chat(client, headers=None, payload=None):
    return client.post("/chat/", headers=headers or {}, json=payload or {})


def _execute_case(client, case):
    kind = case["kind"]

    if kind == "direct":
        headers = client.make_headers(case["role"], agent_id=case.get("agent_id"))
        response = _post_chat(client, headers=headers, payload={"message": case["message"], "tool": TOOL_NAME})
        assert response.status_code == case["expected"]
        data = response.json()
        assert data["tool_used"] == TOOL_NAME
        assert data["message"]
        return

    if kind == "follow_up":
        headers = client.make_headers(case["role"], agent_id=case.get("agent_id"))
        seed = _post_chat(client, headers=headers, payload={"message": "seed", "tool": TOOL_NAME})
        assert seed.status_code == 200
        session_id = seed.json()["session_id"]

        response = _post_chat(
            client,
            headers=headers,
            payload={"message": case["message"], "tool": TOOL_NAME, "session_id": session_id},
        )
        assert response.status_code == case["expected"]
        data = response.json()
        assert data["session_id"] == session_id
        assert data["tool_used"] == TOOL_NAME
        return

    if kind == "unauthenticated":
        response = _post_chat(client, payload={"message": "hello", "tool": TOOL_NAME})
        assert response.status_code == case["expected"]
        return

    if kind == "invalid_token":
        response = _post_chat(
            client,
            headers={"Authorization": "Bearer invalid.token.payload"},
            payload={"message": "hello", "tool": TOOL_NAME},
        )
        assert response.status_code == case["expected"]
        return

    if kind == "wrong_auth_scheme":
        response = _post_chat(
            client,
            headers={"Authorization": "Token abc123"},
            payload={"message": "hello", "tool": TOOL_NAME},
        )
        assert response.status_code == case["expected"]
        return

    if kind == "raw_payload":
        headers = client.make_headers(case["role"], agent_id=case.get("agent_id"))
        response = _post_chat(client, headers=headers, payload=case["payload"])
        assert response.status_code == case["expected"]
        return

    if kind == "random_session":
        headers = client.make_headers(case["role"], agent_id=case.get("agent_id"))
        response = _post_chat(
            client,
            headers=headers,
            payload={"message": "hello", "tool": TOOL_NAME, "session_id": str(uuid.uuid4())},
        )
        assert response.status_code == case["expected"]
        return

    if kind == "cross_owner_session":
        owner_headers = client.make_headers(case["owner_role"])
        seed = _post_chat(client, headers=owner_headers, payload={"message": "owner seed", "tool": TOOL_NAME})
        assert seed.status_code == 200
        owner_session = seed.json()["session_id"]

        requester_headers = client.make_headers(case["requester_role"])
        response = _post_chat(
            client,
            headers=requester_headers,
            payload={"message": "attempt", "tool": TOOL_NAME, "session_id": owner_session},
        )
        assert response.status_code == case["expected"]
        return

    raise AssertionError(f"Unknown case kind: {kind}")


@pytest.mark.parametrize("case", ALL_CASES, ids=[c["id"] for c in ALL_CASES])
def test_comparison_cases(client, case):
    _execute_case(client, case)
