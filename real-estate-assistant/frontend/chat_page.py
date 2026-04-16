"""
Chat page: Simple ChatGPT-like interface.
"""
import streamlit as st
from api_client import send_message, get_sessions, get_messages
from session_store import clear_query_state

TOOLS = {
    "Property Retrieval":      "property_retrieval",
    "Summarization":           "summarization",
    "Market Analysis":         "market_analysis",
    "Comparison":              "comparison",
    "Investment Advice":       "investment_recommendation",
}

ROLE_LABELS = {
    "admin": ("🛡️ Admin",  "badge-admin"),
    "agent": ("🏢 Agent",  "badge-agent"),
    "buyer": ("🛒 Buyer",  "badge-buyer"),
}


def _load_history(session_id: str):
    msgs = get_messages(session_id)
    st.session_state["messages"] = [
        {"sender": m["sender"], "content": m["content"], "tool_used": m.get("tool_used")}
        for m in msgs
    ]


def render():
    role     = st.session_state.get("user_role", "buyer")
    name     = st.session_state.get("user_name", "User")
    user_id  = st.session_state.get("user_id", "")
    agent_id = st.session_state.get("user_agent_id") or ""

    badge_text, badge_cls = ROLE_LABELS.get(role, ("User", "badge-buyer"))

    # ── SIDEBAR ────────────────────────────────────────────────────────────────
    with st.sidebar:
        # User info
        st.markdown(
            f'<div style="padding:1rem 0 0.5rem;">'
            f'<div style="font-weight:600;font-size:0.95rem;color:#e2e8f0;margin-bottom:4px;">👤 {name}</div>'
            f'<span class="{badge_cls}">{badge_text}</span>'
            + (f'<div style="font-size:0.76rem;color:#94a3b8;margin-top:4px;">ID: {agent_id}</div>' if agent_id else '')
            + '</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        # New chat
        if st.button("➕ New Chat", use_container_width=True):
            st.session_state["active_session_id"] = None
            st.session_state["messages"] = []
            st.rerun()

        # Tool picker
        st.caption("Select Tool")
        tool_label = st.selectbox("Tool", list(TOOLS.keys()), label_visibility="collapsed")
        st.session_state["selected_tool"] = TOOLS[tool_label]

        st.divider()

        # Recent chats
        st.caption("Recent Chats")
        sessions = get_sessions(user_id) if user_id else []
        if sessions:
            for s in sessions[:10]:
                label  = (s.get("title") or "Untitled")[:34]
                active = s["id"] == st.session_state.get("active_session_id")
                if st.button(
                    f"{'▸ ' if active else ''}{label}",
                    key=f"s_{s['id']}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                ):
                    st.session_state["active_session_id"] = s["id"]
                    _load_history(s["id"])
                    st.rerun()
        else:
            st.caption("No chats yet.")

        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            clear_query_state()
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # ── MAIN ───────────────────────────────────────────────────────────────────
    # Simple header
    st.markdown(
        '<h3 style="margin:0 0 0.3rem;color:#0f172a;font-size:1.3rem;">🏠 EstateNexa AI</h3>'
        f'<p style="margin:0 0 1rem;color:#64748b;font-size:0.85rem;">Logged in as <b>{name}</b> · {badge_text}</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Messages
    messages = st.session_state.get("messages", [])
    if not messages:
        st.markdown(
            '<div style="text-align:center;padding:3rem 0;color:#94a3b8;">'
            '<div style="font-size:2.5rem;margin-bottom:0.8rem;">💬</div>'
            '<p style="color:#64748b;font-size:1rem;">Ask any real estate question</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for msg in messages:
            if msg["sender"] == "user":
                st.markdown(
                    f'<div class="bubble-user">{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                content = msg["content"]
                tool    = msg.get("tool_used", "")
                tag     = (f'<span class="tool-tag">{tool.replace("_"," ").title()}</span><br>' if tool else "")
                # Check if this is an error message
                if content.startswith("⚠️"):
                    st.markdown(
                        f'<div class="bubble-error">{content}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    looks_like_markdown_table = ("|" in content and "\n|---" in content.replace(" ", ""))
                    if looks_like_markdown_table:
                        st.markdown(f'<div class="bubble-ai">{tag}</div>', unsafe_allow_html=True)
                        st.markdown(content)
                    else:
                        safe_content = (
                            content
                            .replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                            .replace("\n", "<br>")
                        )
                        st.markdown(
                            f'<div class="bubble-ai">{tag}{safe_content}</div>',
                            unsafe_allow_html=True,
                        )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Chat input
    selected_tool = st.session_state.get("selected_tool", "property_retrieval")
    with st.form("chat_form", clear_on_submit=True):
        cols = st.columns([9, 1])
        with cols[0]:
            user_input = st.text_input(
                "msg",
                placeholder=f"Ask about {tool_label.lower()}…",
                label_visibility="collapsed",
            )
        with cols[1]:
            submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state["messages"].append(
            {"sender": "user", "content": user_input, "tool_used": selected_tool}
        )
        session_id = st.session_state.get("active_session_id")
        with st.spinner("Thinking…"):
            data, status = send_message(session_id, user_input, selected_tool)

        if status == 200:
            st.session_state["active_session_id"] = data["session_id"]
            st.session_state["messages"].append({
                "sender":   "assistant",
                "content":  data["message"],
                "tool_used": data.get("tool_used"),
            })
        else:
            err = data.get("detail", "Unexpected error. Please try again.")
            st.session_state["messages"].append({
                "sender":   "assistant",
                "content":  f"⚠️ {err}",
                "tool_used": None,
            })
        st.rerun()
