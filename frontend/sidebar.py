import uuid
import streamlit as st
from config import MODELS
from backend.state import save_state
from backend.storage import delete_session_pdfs, delete_pdf
from backend.vector_store import delete_session_namespace, delete_paper_vectors
from backend.auth import sign_out

THEME_OPTIONS = ["System", "Dark", "Light"]


def _evict_pdf_url_cache(paper_name: str):
    """Remove the cached signed URL for a paper so the PDF viewer
    doesn't serve a stale/dead URL after the paper is deleted."""
    st.session_state.pop(f"pdf_url_cache::{paper_name}", None)


def render_sidebar():
    """Render sidebar. Returns (selected_paper, quick_query)."""
    quick_query    = None
    selected_paper = "🔍 All Papers"

    with st.sidebar:
        # ── Theme selector ────────────────────────────────────────────────────
        current = st.session_state.ui_theme
        if current not in THEME_OPTIONS:
            current = "System"

        chosen_theme = st.selectbox(
            "🎨 Theme", THEME_OPTIONS,
            index=THEME_OPTIONS.index(current)
        )
        if chosen_theme != st.session_state.ui_theme:
            st.session_state.ui_theme = chosen_theme
            st.rerun()

        # ── New chat button ───────────────────────────────────────────────────
        if st.button("＋ New Chat", use_container_width=True, type="primary"):
            st.session_state.session_counter += 1
            new_name = f"Chat {st.session_state.session_counter}"
            # Skip numbers already taken by renamed chats
            while new_name in st.session_state.chat_sessions:
                st.session_state.session_counter += 1
                new_name = f"Chat {st.session_state.session_counter}"
            st.session_state.chat_sessions[new_name] = {
                "id": uuid.uuid4().hex[:8],
                "messages": [], "papers": [], "analysis": {}, "pdf_paths": {}
            }
            st.session_state.active_session = new_name
            st.session_state.renaming = None
            save_state()
            st.rerun()

        st.markdown("### 💬 Chats")

        session_names   = list(st.session_state.chat_sessions.keys())
        active_name     = st.session_state.active_session
        sorted_sessions = [active_name] + [n for n in reversed(session_names) if n != active_name]

        # ── Session list ──────────────────────────────────────────────────────
        with st.container(height=350, border=True):
            for name in sorted_sessions:
                is_active             = (name == active_name)
                col_btn, col_ren, col_del = st.columns([5, 1, 1])

                with col_btn:
                    if st.button(
                        f"{'▶ ' if is_active else ''}{name}",
                        key=f"sess_{name}", use_container_width=True
                    ):
                        st.session_state.active_session = name
                        st.session_state.renaming = None
                        st.rerun()

                with col_ren:
                    if st.button("✏️", key=f"ren_{name}", help="Rename"):
                        st.session_state.renaming = name
                        st.rerun()

                with col_del:
                    if st.button(
                        "🗑", key=f"del_{name}", help="Delete",
                        disabled=len(session_names) <= 1
                    ):
                        user_id    = st.session_state.get("user_id", "anon")
                        session_id = st.session_state.chat_sessions[name]["id"]
                        # Evict URL cache for every paper in the deleted session
                        for p in st.session_state.chat_sessions[name].get("papers", []):
                            _evict_pdf_url_cache(p)
                        delete_session_namespace(name)
                        delete_session_pdfs(user_id, session_id)
                        del st.session_state.chat_sessions[name]
                        if st.session_state.active_session == name:
                            st.session_state.active_session = list(
                                st.session_state.chat_sessions.keys()
                            )[0]
                        save_state()
                        st.rerun()

        # ── Rename ────────────────────────────────────────────────────────────
        if st.session_state.renaming and st.session_state.renaming in st.session_state.chat_sessions:
            old = st.session_state.renaming
            new = st.text_input("New name", value=old, key="rename_input")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("✅ Save", use_container_width=True):
                    if new and new != old and new not in st.session_state.chat_sessions:
                        reordered = {}
                        for k, v in st.session_state.chat_sessions.items():
                            reordered[new if k == old else k] = v
                        st.session_state.chat_sessions = reordered
                        if st.session_state.active_session == old:
                            st.session_state.active_session = new
                        if old in st.session_state.get("vector_stores", {}):
                            st.session_state.vector_stores[new] = \
                                st.session_state.vector_stores.pop(old)
                    elif new in st.session_state.chat_sessions and new != old:
                        st.error(f'"{new}" already exists.')
                    st.session_state.renaming = None
                    save_state()
                    st.rerun()
            with rc2:
                if st.button("✖ Cancel", use_container_width=True):
                    st.session_state.renaming = None
                    st.rerun()

        st.divider()

        # ── Papers in active chat ─────────────────────────────────────────────
        active_name = st.session_state.active_session
        active_sess = st.session_state.chat_sessions[active_name]
        paper_list  = active_sess.get("papers", [])

        st.markdown("### 📂 Papers in this Chat")
        if paper_list:
            papers_to_delete = []
            for i, p in enumerate(paper_list):
                pc1, pc2 = st.columns([6, 1])
                with pc1:
                    st.markdown(f"📄 {p}")
                with pc2:
                    if st.button("✕", key=f"delpaper_{active_name}_{p}_{i}", help=f"Remove {p}"):
                        papers_to_delete.append(p)

            if papers_to_delete:
                sess    = st.session_state.chat_sessions[active_name]
                user_id = st.session_state.get("user_id", "anon")
                for p in papers_to_delete:
                    sess["papers"].remove(p)
                    sess["analysis"].pop(p, None)
                    path = sess.get("pdf_paths", {}).pop(p, None)
                    if path:
                        delete_pdf(path)
                    delete_paper_vectors(active_name, p)
                    # FIX: evict URL cache so the PDF viewer doesn't try to
                    # display a deleted paper via a now-dead signed URL
                    _evict_pdf_url_cache(p)
                save_state()
                st.rerun()
        else:
            st.caption("No papers uploaded in this chat yet.")

        # ── Query scope ───────────────────────────────────────────────────────
        if paper_list:
            st.markdown("### 🔍 Query Scope")
            selected_paper = st.selectbox(
                "scope", ["🔍 All Papers"] + paper_list,
                label_visibility="collapsed",
                key=f"scope_{active_name}"
            )

        st.divider()

        # ── Quick Actions ─────────────────────────────────────────────────────
        st.markdown("### ⚡ Quick Actions")
        if st.button("📝 Summarize all",  use_container_width=True):
            quick_query = "Give a comprehensive summary of each paper covering objectives, methods and key findings."
        if st.button("🔬 Methodology",    use_container_width=True):
            quick_query = "Explain the methodology and research methods used in each paper."
        if st.button("📈 Key Findings",   use_container_width=True):
            quick_query = "What are the key findings, results and contributions of each paper?"
        if st.button("⚠️ Limitations",    use_container_width=True):
            quick_query = "What are the limitations and weaknesses mentioned in each paper?"

        st.divider()

        # ── Clear papers ──────────────────────────────────────────────────────
        if st.button("🗑️ Clear Papers in this Chat", use_container_width=True):
            user_id    = st.session_state.get("user_id", "anon")
            session_id = active_sess["id"]
            # Evict URL cache for all papers before clearing
            for p in active_sess.get("papers", []):
                _evict_pdf_url_cache(p)
            delete_session_namespace(active_name)
            delete_session_pdfs(user_id, session_id)
            active_sess["papers"]    = []
            active_sess["analysis"]  = {}
            active_sess["pdf_paths"] = {}
            save_state()
            st.success("Papers cleared!")
            st.rerun()

        st.divider()

        # ── User info + Logout ────────────────────────────────────────────────
        user_email = st.session_state.user.email if st.session_state.get("user") else ""
        st.caption(f"👤 {user_email}")
        if st.button("🚪 Logout", use_container_width=True):
            sign_out()
            st.rerun()

    return selected_paper, quick_query