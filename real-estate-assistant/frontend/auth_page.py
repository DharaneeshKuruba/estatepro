"""
Auth page: Simple Login + Buyer Registration.
"""
import streamlit as st
from api_client import register_user, login_user
from session_store import save_query_state


def _set_session(data: dict):
    st.session_state["token"]         = data["access_token"]
    st.session_state["user_id"]       = data["user"]["id"]
    st.session_state["user_name"]     = data["user"]["name"]
    st.session_state["user_email"]    = data["user"]["email"]
    st.session_state["user_role"]     = data["user"]["role"]
    st.session_state["user_agent_id"] = data["user"].get("agent_id")
    st.session_state["active_session_id"] = None
    st.session_state["messages"]      = []
    st.session_state["selected_tool"] = "property_retrieval"
    save_query_state()


def _show_msg(kind: str, text: str):
    """Show a message with guaranteed readable contrast."""
    colors = {
        "error":   ("#fff0f0", "#7f1d1d", "#fca5a5"),
        "success": ("#f0fdf4", "#14532d", "#86efac"),
        "warning": ("#fffbeb", "#78350f", "#fcd34d"),
        "info":    ("#eff6ff", "#1e3a5f", "#93c5fd"),
    }
    bg, fg, border = colors.get(kind, colors["info"])
    icons = {"error": "❌", "success": "✅", "warning": "⚠️", "info": "ℹ️"}
    icon = icons.get(kind, "ℹ️")
    st.markdown(
        f'<div style="background:{bg};color:{fg};border:1px solid {border};'
        f'border-radius:8px;padding:10px 14px;font-size:0.9rem;margin:6px 0;">'
        f'{icon} {text}</div>',
        unsafe_allow_html=True,
    )


def render():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        if st.session_state.get("auth_notice"):
            _show_msg("warning", st.session_state.pop("auth_notice"))

        # Header
        st.markdown(
            '<div style="text-align:center;padding:2rem 0 1.5rem;">'
            '<div style="font-size:2.5rem;">🏠</div>'
            '<h2 style="font-size:1.7rem;font-weight:700;color:#0f172a;margin:0.3rem 0 0;">EstateNexa AI</h2>'
            '<p style="color:#64748b;margin:0.2rem 0 0;font-size:0.9rem;">Real Estate Advisory Assistant</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Login", "Register"])

        # ── LOGIN ──────────────────────────────────────────────
        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            role = st.selectbox(
                "Role",
                options=["buyer", "agent", "admin"],
                format_func=lambda r: r.capitalize(),
                key="login_role",
            )

            with st.form("login_form"):
                email    = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                login_btn = st.form_submit_button("Login", use_container_width=True)


            if login_btn:
                if not email or not password:
                    _show_msg("error", "Please enter your email and password.")
                else:
                    with st.spinner("Logging in…"):
                        data, status = login_user(email, password, role=role)
                    if status == 200:
                        _set_session(data)
                        _show_msg("success", f"Welcome, {data['user']['name']}!")
                        st.rerun()
                    else:
                        _show_msg("error", data.get("detail", "Login failed. Check your credentials."))

        # ── REGISTER ───────────────────────────────────────────
        with tab_register:
            st.markdown("<br>", unsafe_allow_html=True)
            st.caption("Buyer accounts only. Admin and agent accounts are pre-configured.")

            with st.form("reg_form"):
                name   = st.text_input("Full Name", placeholder="Jane Doe")
                r_email = st.text_input("Email", placeholder="buyer@example.com")
                r_pass  = st.text_input("Password", type="password", placeholder="Min 6 characters")
                r_conf  = st.text_input("Confirm Password", type="password", placeholder="Repeat password")
                reg_btn = st.form_submit_button("Create Account", use_container_width=True)

            if reg_btn:
                if not name or not r_email or not r_pass:
                    _show_msg("error", "All fields are required.")
                elif r_pass != r_conf:
                    _show_msg("error", "Passwords do not match.")
                elif len(r_pass) < 6:
                    _show_msg("error", "Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating account…"):
                        data, status = register_user(name, r_email, r_pass)
                    if status == 201:
                        _set_session(data)
                        _show_msg("success", f"Account created! Welcome, {name}!")
                        st.rerun()
                    else:
                        _show_msg("error", data.get("detail", "Registration failed. Please try again."))
