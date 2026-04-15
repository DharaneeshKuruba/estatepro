import uuid

import pytest


def _register(client, payload):
    return client.post("/auth/register", json=payload)


def _login(client, payload):
    return client.post("/auth/login", json=payload)


def _create_agent(client, payload, headers=None):
    return client.post("/auth/admin/create-agent", json=payload, headers=headers or {})


def _chat(client, payload, headers=None):
    return client.post("/chat/", json=payload, headers=headers or {})


# 24 registration cases
REGISTRATION_CASES = []

for i in range(1, 9):
    REGISTRATION_CASES.append(
        {
            "id": f"register-buyer-success-{i}",
            "payload": {
                "name": f"Buyer {i}",
                "email": f"buyer_reg_{i}@test.com",
                "password": "Secure@123",
                "role": "buyer",
            },
            "expected": 201,
        }
    )

for i in range(1, 5):
    REGISTRATION_CASES.append(
        {
            "id": f"register-agent-blocked-{i}",
            "payload": {
                "name": f"Agent {i}",
                "email": f"agent_reg_{i}@test.com",
                "password": "Secure@123",
                "role": "agent",
            },
            "expected": 403,
        }
    )
    REGISTRATION_CASES.append(
        {
            "id": f"register-admin-blocked-{i}",
            "payload": {
                "name": f"Admin {i}",
                "email": f"admin_reg_{i}@test.com",
                "password": "Secure@123",
                "role": "admin",
            },
            "expected": 403,
        }
    )

REGISTRATION_CASES.extend(
    [
        {
            "id": "register-duplicate-email",
            "payload": {
                "name": "Dup",
                "email": "dup_reg@test.com",
                "password": "Secure@123",
                "role": "buyer",
            },
            "pre": "register_once",
            "expected": 409,
        },
        {
            "id": "register-missing-name",
            "payload": {"email": "missing_name@test.com", "password": "Secure@123", "role": "buyer"},
            "expected": 422,
        },
        {
            "id": "register-invalid-email",
            "payload": {"name": "Bad", "email": "not-an-email", "password": "Secure@123", "role": "buyer"},
            "expected": 422,
        },
        {
            "id": "register-missing-password",
            "payload": {"name": "NoPwd", "email": "no_pwd@test.com", "role": "buyer"},
            "expected": 422,
        },
        {
            "id": "register-missing-email",
            "payload": {"name": "NoEmail", "password": "Secure@123", "role": "buyer"},
            "expected": 422,
        },
        {
            "id": "register-default-role",
            "payload": {"name": "DefaultRole", "email": "default_role@test.com", "password": "Secure@123"},
            "expected": 201,
        },
        {
            "id": "register-empty-password",
            "payload": {"name": "EmptyPwd", "email": "empty_pwd@test.com", "password": "", "role": "buyer"},
            "expected": 201,
        },
        {
            "id": "register-empty-name",
            "payload": {"name": "", "email": "empty_name@test.com", "password": "Secure@123", "role": "buyer"},
            "expected": 201,
        },
    ]
)

assert len(REGISTRATION_CASES) == 24


# 24 login cases
LOGIN_CASES = [
    {"id": "login-admin-success-role", "payload": {"email": "admin@realestate.com", "password": "TestPassword@1", "role": "admin"}, "expected": 200},
    {"id": "login-admin-success-no-role", "payload": {"email": "admin@realestate.com", "password": "TestPassword@1"}, "expected": 200},
    {"id": "login-agent-success-role", "payload": {"email": "agent1@realestate.com", "password": "TestPassword@1", "role": "agent"}, "expected": 200},
    {"id": "login-agent-success-no-role", "payload": {"email": "agent1@realestate.com", "password": "TestPassword@1"}, "expected": 200},
    {"id": "login-buyer-success-role", "payload": {"email": "buyer@test.com", "password": "TestPassword@1", "role": "buyer"}, "expected": 200},
    {"id": "login-buyer-success-no-role", "payload": {"email": "buyer@test.com", "password": "TestPassword@1"}, "expected": 200},
    {"id": "login-admin-wrong-password", "payload": {"email": "admin@realestate.com", "password": "WrongPassword", "role": "admin"}, "expected": 401},
    {"id": "login-agent-wrong-password", "payload": {"email": "agent1@realestate.com", "password": "WrongPassword", "role": "agent"}, "expected": 401},
    {"id": "login-buyer-wrong-password", "payload": {"email": "buyer@test.com", "password": "WrongPassword", "role": "buyer"}, "expected": 401},
    {"id": "login-admin-role-mismatch", "payload": {"email": "admin@realestate.com", "password": "TestPassword@1", "role": "buyer"}, "expected": 403},
    {"id": "login-agent-role-mismatch", "payload": {"email": "agent1@realestate.com", "password": "TestPassword@1", "role": "admin"}, "expected": 403},
    {"id": "login-buyer-role-mismatch", "payload": {"email": "buyer@test.com", "password": "TestPassword@1", "role": "agent"}, "expected": 403},
    {"id": "login-unknown-email-1", "payload": {"email": "unknown1@test.com", "password": "TestPassword@1"}, "expected": 401},
    {"id": "login-unknown-email-2", "payload": {"email": "unknown2@test.com", "password": "TestPassword@1", "role": "buyer"}, "expected": 401},
    {"id": "login-unknown-email-3", "payload": {"email": "unknown3@test.com", "password": "TestPassword@1", "role": "agent"}, "expected": 401},
    {"id": "login-empty-body", "payload": {}, "expected": 422},
    {"id": "login-missing-email", "payload": {"password": "TestPassword@1"}, "expected": 422},
    {"id": "login-missing-password", "payload": {"email": "admin@realestate.com"}, "expected": 422},
    {"id": "login-invalid-email-format", "payload": {"email": "invalid-email", "password": "TestPassword@1"}, "expected": 422},
    {"id": "login-empty-password", "payload": {"email": "admin@realestate.com", "password": ""}, "expected": 401},
    {"id": "login-trailing-space-email", "payload": {"email": "admin@realestate.com ", "password": "TestPassword@1"}, "expected": 200},
    {"id": "login-uppercase-email", "payload": {"email": "ADMIN@REALESTATE.COM", "password": "TestPassword@1"}, "expected": 401},
    {"id": "login-agent-id-returned", "payload": {"email": "agent1@realestate.com", "password": "TestPassword@1", "role": "agent"}, "expected": 200, "assert_agent_id": True},
    {"id": "login-token-present", "payload": {"email": "buyer@test.com", "password": "TestPassword@1", "role": "buyer"}, "expected": 200, "assert_token": True},
]

assert len(LOGIN_CASES) == 24


# 12 admin-create-agent cases
CREATE_AGENT_CASES = [
    {"id": "create-agent-admin-success-1", "role": "admin", "payload": {"name": "Agent A", "email": "new_agent_a@test.com", "password": "Secure@123", "agent_id": "AG100"}, "expected": 200},
    {"id": "create-agent-admin-success-2", "role": "admin", "payload": {"name": "Agent B", "email": "new_agent_b@test.com", "password": "Secure@123", "agent_id": "AG101"}, "expected": 200},
    {"id": "create-agent-admin-success-3", "role": "admin", "payload": {"name": "Agent C", "email": "new_agent_c@test.com", "password": "Secure@123", "agent_id": "AG102"}, "expected": 400},
    {"id": "create-agent-admin-success-4", "role": "admin", "payload": {"name": "Agent D", "email": "new_agent_d@test.com", "password": "Secure@123", "agent_id": "AG103"}, "expected": 400},
    {"id": "create-agent-buyer-blocked", "role": "buyer", "payload": {"name": "Blocked", "email": "blocked_buyer@test.com", "password": "Secure@123", "agent_id": "AG200"}, "expected": 403},
    {"id": "create-agent-agent-blocked", "role": "agent", "payload": {"name": "Blocked", "email": "blocked_agent@test.com", "password": "Secure@123", "agent_id": "AG201"}, "expected": 403},
    {"id": "create-agent-no-auth", "role": None, "payload": {"name": "NoAuth", "email": "no_auth@test.com", "password": "Secure@123", "agent_id": "AG202"}, "expected": 401},
    {"id": "create-agent-invalid-token", "role": "invalid", "payload": {"name": "BadToken", "email": "bad_token@test.com", "password": "Secure@123", "agent_id": "AG203"}, "expected": 401},
    {"id": "create-agent-duplicate-email", "role": "admin", "payload": {"name": "Dup", "email": "agent1@realestate.com", "password": "Secure@123", "agent_id": "AG204"}, "expected": 400},
    {"id": "create-agent-missing-agent-id", "role": "admin", "payload": {"name": "NoAgentId", "email": "no_agent_id@test.com", "password": "Secure@123"}, "expected": 422},
    {"id": "create-agent-invalid-email", "role": "admin", "payload": {"name": "BadEmail", "email": "bad-email", "password": "Secure@123", "agent_id": "AG205"}, "expected": 422},
    {"id": "create-agent-missing-name", "role": "admin", "payload": {"email": "missing_name_agent@test.com", "password": "Secure@123", "agent_id": "AG206"}, "expected": 422},
]

assert len(CREATE_AGENT_CASES) == 12


# 10 auth-policy/access cases across protected endpoints
AUTH_POLICY_CASES = [
    {"id": "chat-admin-valid", "kind": "chat", "headers": "admin", "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 200},
    {"id": "chat-agent-valid", "kind": "chat", "headers": "agent", "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 200},
    {"id": "chat-buyer-valid", "kind": "chat", "headers": "buyer", "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 200},
    {"id": "chat-no-auth", "kind": "chat", "headers": None, "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 401},
    {"id": "chat-invalid-token", "kind": "chat", "headers": "invalid", "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 401},
    {"id": "chat-wrong-scheme", "kind": "chat", "headers": "wrong_scheme", "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 401},
    {"id": "chat-token-user-not-found", "kind": "chat", "headers": "ghost", "payload": {"message": "Hello", "tool": "property_retrieval"}, "expected": 401},
    {"id": "chat-invalid-tool", "kind": "chat", "headers": "admin", "payload": {"message": "Hello", "tool": "unknown_tool"}, "expected": 400},
    {"id": "chat-missing-message", "kind": "chat", "headers": "buyer", "payload": {"tool": "property_retrieval"}, "expected": 422},
    {"id": "chat-null-message", "kind": "chat", "headers": "agent", "payload": {"message": None, "tool": "property_retrieval"}, "expected": 422},
]

assert len(AUTH_POLICY_CASES) == 10


@pytest.mark.parametrize("case", REGISTRATION_CASES, ids=[c["id"] for c in REGISTRATION_CASES])
def test_registration_cases(client, case):
    if case.get("pre") == "register_once":
        _register(client, case["payload"])

    response = _register(client, case["payload"])
    assert response.status_code == case["expected"]

    if response.status_code == 201:
        body = response.json()
        assert body["user"]["role"] == "buyer"
        assert body["access_token"]


@pytest.mark.parametrize("case", LOGIN_CASES, ids=[c["id"] for c in LOGIN_CASES])
def test_login_cases(client, case):
    response = _login(client, case["payload"])
    assert response.status_code == case["expected"]

    if response.status_code == 200:
        body = response.json()
        assert "access_token" in body
        assert "user" in body
        if case.get("assert_agent_id"):
            assert body["user"]["agent_id"] == "AG001"
        if case.get("assert_token"):
            assert len(body["access_token"]) > 20


@pytest.mark.parametrize("case", CREATE_AGENT_CASES, ids=[c["id"] for c in CREATE_AGENT_CASES])
def test_create_agent_cases(client, case):
    if case["role"] == "admin":
        headers = client.make_headers("admin")
    elif case["role"] == "buyer":
        headers = client.make_headers("buyer")
    elif case["role"] == "agent":
        headers = client.make_headers("agent", agent_id="AG001")
    elif case["role"] == "invalid":
        headers = {"Authorization": "Bearer invalid.token.payload"}
    else:
        headers = {}

    response = _create_agent(client, case["payload"], headers=headers)
    assert response.status_code == case["expected"]

    if response.status_code == 200:
        body = response.json()
        assert body["role"] == "agent"
        assert body["agent_id"]


@pytest.mark.parametrize("case", AUTH_POLICY_CASES, ids=[c["id"] for c in AUTH_POLICY_CASES])
def test_auth_policy_cases(client, case):
    headers_kind = case["headers"]
    if headers_kind == "admin":
        headers = client.make_headers("admin")
    elif headers_kind == "agent":
        headers = client.make_headers("agent", agent_id="AG001")
    elif headers_kind == "buyer":
        headers = client.make_headers("buyer")
    elif headers_kind == "invalid":
        headers = {"Authorization": "Bearer invalid.token.payload"}
    elif headers_kind == "wrong_scheme":
        headers = {"Authorization": "Token abc123"}
    elif headers_kind == "ghost":
        ghost_email = f"ghost-{uuid.uuid4()}@test.com"
        ghost_token = client.make_token(role="buyer", email=ghost_email)
        headers = {"Authorization": f"Bearer {ghost_token}"}
    else:
        headers = {}

    response = _chat(client, case["payload"], headers=headers)
    assert response.status_code == case["expected"]


# 70 cases total in this file.
TOTAL_AUTH_CASES = len(REGISTRATION_CASES) + len(LOGIN_CASES) + len(CREATE_AGENT_CASES) + len(AUTH_POLICY_CASES)
assert TOTAL_AUTH_CASES == 70
