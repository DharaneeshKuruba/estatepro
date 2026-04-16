import streamlit as st

PERSIST_KEYS = [
    "token",
    "user_id",
    "user_name",
    "user_email",
    "user_role",
    "user_agent_id",
    "active_session_id",
    "selected_tool",
]


def save_query_state() -> None:
    """Persist key session values to URL query params so refresh keeps login/session."""
    qp = st.query_params
    for key in PERSIST_KEYS:
        val = st.session_state.get(key)
        if val in (None, ""):
            if key in qp:
                del qp[key]
        else:
            qp[key] = str(val)


def restore_query_state() -> None:
    """Restore persisted values from URL query params into session_state."""
    qp = st.query_params
    for key in PERSIST_KEYS:
        val = qp.get(key)
        if val is not None and key not in st.session_state:
            st.session_state[key] = val


def clear_query_state() -> None:
    """Remove persisted session values from URL query params."""
    qp = st.query_params
    for key in PERSIST_KEYS:
        if key in qp:
            del qp[key]
