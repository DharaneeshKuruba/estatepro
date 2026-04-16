"""
EstatePro AI — Main Streamlit app.
Simple, clean, high-contrast theme.
"""
import streamlit as st
import auth_page
import chat_page
from session_store import restore_query_state, save_query_state, clear_query_state

st.set_page_config(
    page_title="EstateNexa AI",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
:root {
    --bg-main: #f5f7fa;
    --bg-card: #ffffff;
    --text-main: #0f172a;
    --text-muted: #334155;
    --border-main: #cbd5e1;
    --focus-ring: #2563eb;
}

/* Sidebar */
[data-testid="stSidebar"] { background-color: #1e2435 !important; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] div { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #2c3347 !important;
    color: #e2e8f0 !important;
    border: 1px solid #3d4560 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background-color: #2563eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100% !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background-color: #1d4ed8 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] [role="listbox"] {
    background-color: #111827 !important;
    border: 1px solid #334155 !important;
}
[data-testid="stSidebar"] [role="option"] {
    background-color: #111827 !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] [role="option"][aria-selected="true"] {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
}

/* Main */
.stApp { background-color: var(--bg-main) !important; color: var(--text-main) !important; }
.main .block-container { padding: 1.5rem 2rem !important; max-width: 900px; }
[data-testid="stAppViewContainer"] .main,
[data-testid="stAppViewContainer"] .main p,
[data-testid="stAppViewContainer"] .main li,
[data-testid="stAppViewContainer"] .main span,
[data-testid="stAppViewContainer"] .main strong,
[data-testid="stAppViewContainer"] .main em,
[data-testid="stAppViewContainer"] .main h1,
[data-testid="stAppViewContainer"] .main h2,
[data-testid="stAppViewContainer"] .main h3,
[data-testid="stAppViewContainer"] .main h4,
[data-testid="stAppViewContainer"] .main h5,
[data-testid="stAppViewContainer"] .main h6,
[data-testid="stAppViewContainer"] .main .stMarkdown,
[data-testid="stAppViewContainer"] .main .stMarkdown * {
    color: #0f172a !important;
}
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] * {
    color: #0f172a !important;
    opacity: 1 !important;
}
[data-testid="stMarkdownContainer"] code {
    background: #e2e8f0 !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    padding: 0.05rem 0.35rem !important;
}
[data-testid="stMarkdownContainer"] pre {
    background: #f8fafc !important;
    border: 1px solid #cbd5e1 !important;
}
[data-testid="stMarkdownContainer"] pre code {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
[data-testid="stAppViewContainer"] .main [data-testid="stHorizontalBlock"],
[data-testid="stAppViewContainer"] .main [data-testid="stVerticalBlock"] {
    color: var(--text-main) !important;
}

/* Fix Streamlit alert/error contrast — override default red-on-red */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
}
/* Error: white text on solid red */
div[data-testid="stAlert"][data-baseweb="notification"][kind="error"],
.stAlert [data-testid="stNotificationContentError"] {
    background-color: #dc2626 !important;
    color: #ffffff !important;
}
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span { color: inherit !important; }

/* Chat bubbles */
.bubble-user {
    background-color: #2563eb;
    color: #ffffff;
    padding: 10px 15px;
    border-radius: 18px 18px 4px 18px;
    margin: 6px 0 6px auto;
    max-width: 70%;
    display: block;
    font-size: 0.94rem;
    line-height: 1.5;
    word-break: break-word;
}
.bubble-ai {
    background-color: #ffffff;
    color: #1e293b;
    padding: 10px 15px;
    border-radius: 18px 18px 18px 4px;
    margin: 6px auto 6px 0;
    max-width: 78%;
    display: block;
    font-size: 0.94rem;
    line-height: 1.6;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    word-break: break-word;
}
.bubble-error {
    background-color: #fef2f2;
    color: #991b1b;
    border: 1px solid #fca5a5;
    padding: 10px 15px;
    border-radius: 12px;
    margin: 6px auto 6px 0;
    max-width: 78%;
    font-size: 0.92rem;
}
.tool-tag {
    background-color: #dbeafe;
    color: #1e40af;
    font-size: 0.72rem;
    font-weight: 600;
    border-radius: 999px;
    padding: 2px 8px;
    display: inline-block;
    margin-bottom: 5px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Markdown table rendering */
.stMarkdown table {
    border-collapse: collapse !important;
    width: 100% !important;
    margin: 0.35rem 0 0.7rem 0 !important;
    background: #ffffff !important;
}
.stMarkdown table th,
.stMarkdown table td {
    border: 1px solid #cbd5e1 !important;
    padding: 8px 10px !important;
    text-align: left !important;
    vertical-align: top !important;
    color: #0f172a !important;
}
.stMarkdown table th {
    background: #eff6ff !important;
    color: #1e3a8a !important;
}

/* Role badges */
.badge-admin { background:#fef3c7; color:#92400e; padding:2px 10px; border-radius:999px; font-size:0.74rem; font-weight:700; }
.badge-agent { background:#d1fae5; color:#065f46; padding:2px 10px; border-radius:999px; font-size:0.74rem; font-weight:700; }
.badge-buyer { background:#ede9fe; color:#4c1d95; padding:2px 10px; border-radius:999px; font-size:0.74rem; font-weight:700; }
.badge-admin { color:#92400e !important; background:#fef3c7 !important; }
.badge-agent { color:#065f46 !important; background:#d1fae5 !important; }
.badge-buyer { color:#4c1d95 !important; background:#ede9fe !important; }

/* Inputs */
.stTextInput > div > div > input {
    background-color: var(--bg-card) !important;
    color: var(--text-main) !important;
    border: 1px solid var(--border-main) !important;
    border-radius: 8px !important;
    caret-color: var(--text-main) !important;
}
.stTextInput > div > div > input::placeholder {
    color: var(--text-muted) !important;
    opacity: 1 !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--focus-ring) !important;
    box-shadow: 0 0 0 1px var(--focus-ring) !important;
}
.stTextInput > label { color: #374151 !important; font-weight: 500 !important; }
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] input {
    color: var(--text-main) !important;
    caret-color: var(--text-main) !important;
}
[data-baseweb="input"] input::placeholder,
[data-baseweb="textarea"] textarea::placeholder,
[data-baseweb="select"] input::placeholder {
    color: var(--text-muted) !important;
    opacity: 1 !important;
}
[data-testid="stAppViewContainer"] .main [data-baseweb="select"] *,
[data-testid="stAppViewContainer"] .main [role="listbox"] *,
[data-testid="stAppViewContainer"] .main [role="option"] * {
    color: var(--text-main) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab"] { color: #64748b !important; font-weight: 500; }
.stTabs [aria-selected="true"] { color: #2563eb !important; border-bottom-color: #2563eb !important; }

/* Buttons Submit */
[data-testid="stFormSubmitButton"] button,
.stForm [data-testid="stFormSubmitButton"] button {
    background-color: #2563eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stFormSubmitButton"] button:hover,
.stForm [data-testid="stFormSubmitButton"] button:hover {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


def main():
    if "_query_restored" not in st.session_state:
        restore_query_state()
        st.session_state["_query_restored"] = True

    defaults = {
        "token": None, "user_id": None, "user_name": None,
        "user_email": None, "user_role": None, "user_agent_id": None,
        "active_session_id": None, "messages": [], "page": "login",
        "selected_tool": "property_retrieval",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if st.session_state["token"]:
        save_query_state()
    else:
        clear_query_state()

    if not st.session_state["token"]:
        auth_page.render()
    else:
        chat_page.render()


if __name__ == "__main__":
    main()
