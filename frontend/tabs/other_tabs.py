import time
import base64
import requests
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

# Max PDF size to embed as base64 (20 MB). Above this we fall back to a
# download button + warning, since a 20 MB base64 string is ~27 MB of HTML
# which can make the page sluggish.
_MAX_EMBED_BYTES = 20 * 1024 * 1024


def _get_cached_pdf_url(paper_name: str, storage_path: str) -> str:
    """Return a signed URL for *paper_name*, generating one only when needed."""
    cache_key = f"pdf_url_cache::{paper_name}"
    now       = time.time()
    cached    = st.session_state.get(cache_key)

    if cached and now < cached["expires_at"] - _URL_REFRESH_AT:
        return cached["url"]

    url = get_pdf_url(storage_path, expires_in=_URL_TTL)
    st.session_state[cache_key] = {
        "url":        url,
        "expires_at": now + _URL_TTL,
        "path":       storage_path,
    }
    return url


def _get_pdf_b64(paper_name: str, url: str) -> str | None:
    """Fetch PDF bytes from *url* and return a base64-encoded string.

    Result is cached in session_state keyed by paper name so repeated
    reruns (chat messages, tab switches) don't re-download the file.

    Why base64 / data URL instead of an iframe with the raw signed URL?
    ──────────────────────────────────────────────────────────────────
    Chrome and Edge block <iframe> / <embed> tags that load PDFs from
    third-party origins when the server sends restrictive
    X-Frame-Options or Content-Security-Policy headers — which Supabase
    Storage does.  Firefox is more permissive, so it worked there while
    Chrome showed "This page has been blocked by Chrome".

    A data: URL is same-origin by definition, so Chrome's frame-blocking
    rules never apply and the built-in PDF viewer renders normally.
    """
    cache_key = f"pdf_b64_cache::{paper_name}"
    cached    = st.session_state.get(cache_key)
    if cached is not None:
        return cached  # "" means a previous fetch failed — don't retry

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        if len(resp.content) > _MAX_EMBED_BYTES:
            # Store sentinel so we don't retry on every rerun
            st.session_state[cache_key] = "__too_large__"
            return "__too_large__"

        b64 = base64.b64encode(resp.content).decode("utf-8")
        st.session_state[cache_key] = b64
        return b64

    except Exception as e:
        st.session_state[cache_key] = ""   # sentinel — failed
        st.error(f"❌ Could not load PDF: {e}")
        return None


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

    # Step 1: get (or refresh) the short-lived signed URL — one Supabase call
    # at most every 6 hours per paper.
    url = _get_cached_pdf_url(chosen_pdf, storage_path)

    # Step 2: fetch bytes and encode — cached in session_state after the first
    # load so subsequent reruns are instant.
    with st.spinner("Loading PDF…"):
        b64 = _get_pdf_b64(chosen_pdf, url)

    if b64 == "__too_large__":
        st.warning(
            f"⚠️ **{chosen_pdf}** is larger than 20 MB and cannot be embedded directly. "
            "Use the download button below to open it in your PDF reader."
        )
        # Still offer a direct-download link via the signed URL
        st.markdown(
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
            f'<button style="padding:0.5rem 1rem;cursor:pointer;">⬇️ Open / Download PDF</button>'
            f'</a>',
            unsafe_allow_html=True,
        )
        return

    if not b64:
        # Error already shown inside _get_pdf_b64
        return

    # Step 3: render via data URL — works in Chrome, Edge, Firefox, Safari.
    # <embed> with a data: URL is never subject to X-Frame-Options or CSP
    # frame-ancestor restrictions because there is no network request.
    st.markdown(
        f'<embed '
        f'src="data:application/pdf;base64,{b64}" '
        f'width="100%" height="800px" '
        f'type="application/pdf" '
        f'style="border:none; border-radius:4px;"'
        f'>',
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
