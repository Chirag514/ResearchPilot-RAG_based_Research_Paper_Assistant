from backend.clients import get_embeddings
from backend.auth import is_authenticated
from backend.state import load_state
from frontend.theme import apply_theme
from frontend.auth_page import render_auth_page
from frontend.sidebar import render_sidebar
from frontend.tabs.chat_tab import render_chat_tab
from frontend.tabs.other_tabs import render_analysis_tab, render_pdf_tab, render_tools_tab
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# LangSmith — auto-traces all LangChain calls (rag_query, auto_analyze, etc.)
# LangSmith — only enabled when LANGCHAIN_TRACING_V2=true in .env
if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
    try:
        api_key = os.getenv("LANGCHAIN_API_KEY") or st.secrets.get("LANGCHAIN_API_KEY", "")
        project = os.getenv("LANGCHAIN_PROJECT") or st.secrets.get("LANGCHAIN_PROJECT", "rag-app")
    except Exception:
        # No secrets.toml — fall back to env vars only
        api_key = os.getenv("LANGCHAIN_API_KEY", "")
        project = os.getenv("LANGCHAIN_PROJECT", "rag-app")
    os.environ["LANGCHAIN_API_KEY"] = api_key
    os.environ["LANGCHAIN_PROJECT"] = project


st.set_page_config(page_title="ResearchPilot : Research Paper Assistant", page_icon="🔬", layout="wide")

# ── Guards ─────────────────────────────────────────────────────────────────────
if not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ Add GROQ_API_KEY to .env and restart.")
    st.stop()
if not os.getenv("PINECONE_API_KEY"):
    st.error("⚠️ Add PINECONE_API_KEY to .env and restart.")
    st.stop()
if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
    st.error("⚠️ Add SUPABASE_URL and SUPABASE_KEY to .env and restart.")
    st.stop()
if not os.getenv("SUPABASE_SERVICE_KEY"):
    st.error("⚠️ Add SUPABASE_SERVICE_KEY to .env and restart.")
    st.stop()

# ── Preload embedding model silently (cached — free on subsequent calls) ───────
# Done BEFORE auth gate so it's ready when user logs in, no spinner on login page
get_embeddings()

# Keeps Supabase alive — one tiny DB read every 5 min via UptimeRobot
try:
    from backend.clients import get_supabase_admin
    get_supabase_admin().table("chat_state").select("id").limit(1).execute()
except Exception:
    pass

# ── Theme ──────────────────────────────────────────────────────────────────────
if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "System"
apply_theme()

# ── Auth gate ──────────────────────────────────────────────────────────────────
if not is_authenticated():
    render_auth_page()
    st.stop()

# ── Session state init ─────────────────────────────────────────────────────────
if "initialized" not in st.session_state:
    saved = load_state()
    st.session_state.chat_sessions   = saved["sessions"]
    st.session_state.active_session  = saved["active"]
    st.session_state.session_counter = saved["counter"]
    st.session_state.selected_model  = "🧠 LLaMA 3.3 70B (Best Quality)"
    st.session_state.renaming        = None
    st.session_state.vector_stores   = {}
    st.session_state.initialized     = True
    # Ensure pdf_paths exists in every session (handles old saved data)
    for sess in st.session_state.chat_sessions.values():
        sess.setdefault("pdf_paths", {})
        sess.pop("pdf_bytes", None)   # remove legacy key

# ── Sidebar ────────────────────────────────────────────────────────────────────
selected_paper, quick_query = render_sidebar()

# ── Title ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="margin:0; padding:0.2rem 0 0.4rem 0;">🔬 ResearchPilot : Research Paper Assistant</h1>',
    unsafe_allow_html=True
)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_chat, tab_analysis, tab_pdf, tab_tools = st.tabs([
    "💬 Chat", "📊 Paper Analysis", "📄 PDF Viewer", "🛠️ Tools"
])

with tab_chat:
    render_chat_tab(selected_paper, quick_query)

with tab_analysis:
    render_analysis_tab()

with tab_pdf:
    render_pdf_tab()

with tab_tools:
    render_tools_tab()
