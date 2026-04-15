import uuid

ROLE_MATRIX = [
    ("admin", None),
    ("agent", "AG001"),
    ("buyer", None),
]

EDGE_MESSAGES = [
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
    "{\"query\": \"structured\"}",
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


def build_tool_cases(tool_name: str):
    cases = []

    # 45 direct role-based and edge-message cases
    for role, agent_id in ROLE_MATRIX:
        for i, message in enumerate(EDGE_MESSAGES, start=1):
            cases.append(
                {
                    "id": f"{tool_name}-{role}-direct-{i}",
                    "kind": "direct",
                    "role": role,
                    "agent_id": agent_id,
                    "message": message,
                    "expected": 200,
                }
            )

    # 15 session continuity cases
    for role, agent_id in ROLE_MATRIX:
        for i, message in enumerate(FOLLOW_UP_MESSAGES, start=1):
            cases.append(
                {
                    "id": f"{tool_name}-{role}-followup-{i}",
                    "kind": "follow_up",
                    "role": role,
                    "agent_id": agent_id,
                    "message": message,
                    "expected": 200,
                }
            )

    # 10 negative/access-policy cases
    cases.extend(
        [
            {"id": f"{tool_name}-unauthenticated", "kind": "unauthenticated", "expected": 401},
            {"id": f"{tool_name}-invalid-token", "kind": "invalid_token", "expected": 401},
            {"id": f"{tool_name}-wrong-auth-scheme", "kind": "wrong_auth_scheme", "expected": 401},
            {
                "id": f"{tool_name}-missing-message-admin",
                "kind": "raw_payload",
                "role": "admin",
                "payload": {"tool": tool_name},
                "expected": 422,
            },
            {
                "id": f"{tool_name}-null-message-agent",
                "kind": "raw_payload",
                "role": "agent",
                "agent_id": "AG001",
                "payload": {"tool": tool_name, "message": None},
                "expected": 422,
            },
            {
                "id": f"{tool_name}-empty-body-buyer",
                "kind": "raw_payload",
                "role": "buyer",
                "payload": {},
                "expected": 422,
            },
            {
                "id": f"{tool_name}-random-session-admin",
                "kind": "random_session",
                "role": "admin",
                "expected": 404,
            },
            {
                "id": f"{tool_name}-random-session-agent",
                "kind": "random_session",
                "role": "agent",
                "agent_id": "AG001",
                "expected": 404,
            },
            {
                "id": f"{tool_name}-random-session-buyer",
                "kind": "random_session",
                "role": "buyer",
                "expected": 404,
            },
            {
                "id": f"{tool_name}-cross-owner-session",
                "kind": "cross_owner_session",
                "owner_role": "admin",
                "requester_role": "buyer",
                "expected": 404,
            },
        ]
    )

    assert len(cases) == 70
    return cases


def _post_chat(client, headers=None, payload=None):
    return client.post("/chat/", headers=headers or {}, json=payload or {})


def execute_tool_case(client, case: dict, tool_name: str):
    kind = case["kind"]

    if kind == "direct":
        headers = client.make_headers(case["role"], agent_id=case.get("agent_id"))
        payload = {"message": case["message"], "tool": tool_name}
        response = _post_chat(client, headers=headers, payload=payload)
        assert response.status_code == case["expected"]
        data = response.json()
        assert data["tool_used"] == tool_name
        assert data["message"]
        return

    if kind == "follow_up":
        headers = client.make_headers(case["role"], agent_id=case.get("agent_id"))
        seed = _post_chat(client, headers=headers, payload={"message": "seed", "tool": tool_name})
        assert seed.status_code == 200
        session_id = seed.json()["session_id"]

        response = _post_chat(
            client,
            headers=headers,
            payload={"message": case["message"], "tool": tool_name, "session_id": session_id},
        )
        assert response.status_code == case["expected"]
        data = response.json()
        assert data["session_id"] == session_id
        assert data["tool_used"] == tool_name
        return

    if kind == "unauthenticated":
        response = _post_chat(client, payload={"message": "hello", "tool": tool_name})
        assert response.status_code == case["expected"]
        return

    if kind == "invalid_token":
        response = _post_chat(
            client,
            headers={"Authorization": "Bearer invalid.token.payload"},
            payload={"message": "hello", "tool": tool_name},
        )
        assert response.status_code == case["expected"]
        return

    if kind == "wrong_auth_scheme":
        response = _post_chat(
            client,
            headers={"Authorization": "Token abc123"},
            payload={"message": "hello", "tool": tool_name},
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
        payload = {
            "message": "hello",
            "tool": tool_name,
            "session_id": str(uuid.uuid4()),
        }
        response = _post_chat(client, headers=headers, payload=payload)
        assert response.status_code == case["expected"]
        return

    if kind == "cross_owner_session":
        owner_headers = client.make_headers(case["owner_role"])
        seed = _post_chat(client, headers=owner_headers, payload={"message": "owner seed", "tool": tool_name})
        assert seed.status_code == 200
        owner_session = seed.json()["session_id"]

        requester_headers = client.make_headers(case["requester_role"])
        response = _post_chat(
            client,
            headers=requester_headers,
            payload={"message": "attempt", "tool": tool_name, "session_id": owner_session},
        )
        assert response.status_code == case["expected"]
        return

    raise AssertionError(f"Unknown case kind: {kind}")
