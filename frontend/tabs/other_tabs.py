import time
import streamlit as st
from backend.rag import rag_query
from backend.storage import get_pdf_url


# ── TAB 2: Paper Analysis ──────────────────────────────────────────────────────
def render_analysis_tab():
    st.subheader("📊 Auto-extracted Paper Summaries")
    active_sess = st.session_state.chat_sessions[st.session_state.active_session]
    analysis    = active_sess.get("analysis", {})
    if not analysis:
        st.info("Upload and process papers to see their analysis here.")
    else:
        for name, text in analysis.items():
            with st.expander(f"📄 {name}", expanded=True):
                st.markdown(text)


# ── TAB 3: PDF Viewer ──────────────────────────────────────────────────────────

# How long (seconds) before expiry we proactively refresh the signed URL.
# Supabase URLs expire after 6 h (21 600 s); we refresh 5 min early.
_URL_TTL        = 21_600   # seconds — must match expires_in in storage.get_pdf_url()
_URL_REFRESH_AT = 300      # refresh when < 5 min remain


def _get_cached_pdf_url(paper_name: str, storage_path: str) -> str:
    """Return a signed URL for *paper_name*, generating one only when needed.

    Three cases that trigger a new Supabase API call:
      1. No cached URL exists yet (first view of this paper).
      2. The user switched to a different paper (cache key changed).
      3. The cached URL is within _URL_REFRESH_AT seconds of expiry.

    All other reruns (chat messages, button clicks, tab switches) reuse the
    cached string — the iframe src stays identical so the browser never reloads
    the PDF and the user keeps their scroll position.
    """
    cache_key = f"pdf_url_cache::{paper_name}"
    now       = time.time()
    cached    = st.session_state.get(cache_key)

    # Reuse if still fresh
    if cached and now < cached["expires_at"] - _URL_REFRESH_AT:
        return cached["url"]

    # Generate a fresh signed URL (one Supabase API call)
    url = get_pdf_url(storage_path, expires_in=_URL_TTL)
    st.session_state[cache_key] = {
        "url":        url,
        "expires_at": now + _URL_TTL,
        "path":       storage_path,
    }
    return url


def render_pdf_tab():
    st.subheader("📄 PDF Viewer")
    active_sess    = st.session_state.chat_sessions[st.session_state.active_session]
    pdf_paths_dict = active_sess.get("pdf_paths", {})
    pdf_papers     = active_sess.get("papers", [])
    viewable       = [p for p in pdf_papers if p in pdf_paths_dict]

    if not viewable:
        st.info("Upload and process papers to view them here.")
        return

    chosen_pdf = st.selectbox("Select a paper to view", viewable, key="pdf_viewer_select")
    if not chosen_pdf:
        return

    storage_path = pdf_paths_dict[chosen_pdf]

    # FIX — Problem 1 (Scroll Reset) + Problem 2 (Expiration) + Problem 3 (Rate Limiting):
    # Generate the signed URL once and cache it in session_state.
    # Every subsequent rerun reuses the exact same URL string so the iframe
    # src attribute never changes → browser keeps the PDF at the current page.
    # The cache is refreshed automatically 5 minutes before it would expire.
    url = _get_cached_pdf_url(chosen_pdf, storage_path)

    st.markdown(
        f'<iframe src="{url}" width="100%" height="800" '
        f'type="application/pdf" style="border:none;"></iframe>',
        unsafe_allow_html=True,
    )


# ── TAB 4: Tools ──────────────────────────────────────────────────────────────
def render_tools_tab():
    st.subheader("🛠️ Research Tools")
    active_name = st.session_state.active_session
    papers      = st.session_state.chat_sessions[active_name].get("papers", [])

    tool = st.selectbox("Choose a tool", [
        "Generate Quiz Questions",
        "Extract All Statistics & Numbers",
        "Find Research Gaps",
        "Compare Papers",
    ])

    tool_key = f"tool_result_{active_name}"
    if st.session_state.get(f"tool_last_{active_name}") != tool:
        st.session_state.pop(tool_key, None)
    st.session_state[f"tool_last_{active_name}"] = tool

    if tool == "Generate Quiz Questions":
        n = st.slider("Number of questions", 3, 15, 5)
        if st.button("Generate Quiz"):
            with st.spinner("Generating..."):
                r = rag_query(
                    f"Generate {n} quiz questions with answers from the papers. "
                    "For each question mention which paper and page it comes from.\n"
                    "Format:\nQ1: [question]\nA1: [answer] (Source: paper, Page X)",
                    active_name
                )
            st.session_state[tool_key] = r["answer"]
        if st.session_state.get(tool_key):
            st.markdown(st.session_state[tool_key])

    elif tool == "Extract All Statistics & Numbers":
        if st.button("Extract Statistics"):
            with st.spinner("Extracting..."):
                r = rag_query(
                    "List ALL statistics, numbers, percentages, metrics, accuracy scores, "
                    "dataset sizes from ALL papers. Group results by paper name. "
                    "Mention page for each stat. Format as bullet points.",
                    active_name
                )
            st.session_state[tool_key] = r["answer"]
        if st.session_state.get(tool_key):
            st.markdown(st.session_state[tool_key])

    elif tool == "Find Research Gaps":
        if st.button("Find Gaps"):
            with st.spinner("Analysing..."):
                r = rag_query(
                    "Based on limitations and future work in ALL papers, "
                    "list open problems not yet solved. Group by paper. "
                    "Cite paper name and page for each gap.",
                    active_name
                )
            st.session_state[tool_key] = r["answer"]
        if st.session_state.get(tool_key):
            st.markdown(st.session_state[tool_key])

    elif tool == "Compare Papers":
        if len(papers) < 2:
            st.info("Upload at least 2 papers to this chat to compare.")
        else:
            p1     = st.selectbox("Paper 1", papers, key="p1")
            p2     = st.selectbox("Paper 2", papers, key="p2", index=min(1, len(papers) - 1))
            aspect = st.selectbox("Compare by", [
                "Overall", "Methodology", "Results",
                "Datasets used", "Problem statement", "Contributions",
            ])
            if st.button("Compare"):
                with st.spinner("Comparing..."):
                    r = rag_query(
                        f"Compare '{p1}' and '{p2}' on: {aspect}. "
                        "Structured format with similarities and differences. "
                        "Always cite paper name and page.",
                        active_name
                    )
                st.session_state[tool_key] = r["answer"]
            if st.session_state.get(tool_key):
                st.markdown(st.session_state[tool_key])