import streamlit as st
from config import MODELS
from backend.state import save_state
from backend.vector_store import get_vs, create_vs
from backend.rag import rag_query, rag_query_stream
from backend.pdf_processor import process_files_parallel


def render_chat_tab(selected_paper: str, quick_query: str):
    active_name = st.session_state.active_session
    active_sess = st.session_state.chat_sessions[active_name]

    # Ensure pdf_paths exists (handles old saved sessions)
    if "pdf_paths" not in active_sess:
        active_sess["pdf_paths"] = {}
    # Remove legacy pdf_bytes if present
    active_sess.pop("pdf_bytes", None)

    # ── Floating scroll button ────────────────────────────────────────────────
    # NOTE: The CSS for .floating-scroll-btn is defined once in theme.py.
    # Only inject the anchor link + tab-visibility JS here to avoid duplication.
    st.markdown("""
    <a href="#bottom-anchor" target="_self" class="floating-scroll-btn" title="Scroll to bottom">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 13l5 5 5-5M7 6l5 5 5-5"/>
        </svg>
    </a>
    <script>
    function syncScrollBtn() {
        const btn = document.querySelector('.floating-scroll-btn');
        if (!btn) return;
        const activeTab = document.querySelector('[role="tab"][aria-selected="true"]');
        if (!activeTab) return;
        const label = (activeTab.textContent || activeTab.innerText || '').trim();
        btn.style.display = label.includes('Chat') ? 'flex' : 'none';
    }
    syncScrollBtn();
    setInterval(syncScrollBtn, 200);
    const obs = new MutationObserver(syncScrollBtn);
    obs.observe(document.body, {subtree: true, attributes: true, attributeFilter: ['aria-selected']});
    </script>
    """, unsafe_allow_html=True)

    # ── Chat history ──────────────────────────────────────────────────────────
    for msg in active_sess["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("📄 View Sources"):
                    for src in msg["sources"]:
                        st.markdown(src["label"])
                        st.caption(src["snippet"])

    st.markdown('<div id="bottom-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div style="height: 10px;"></div>', unsafe_allow_html=True)

    # ── Upload & Model popover ────────────────────────────────────────────────
    t_col1, t_col2, t_col3 = st.columns([1.5, 1.5, 7])

    with t_col1:
        with st.popover("➕ Upload", use_container_width=True):
            uploaded_files = st.file_uploader(
                "PDF only", type="pdf", accept_multiple_files=True,
                label_visibility="collapsed", key=f"uploader_{active_name}"
            )
            if st.button("📥 Process Papers", use_container_width=True):
                if not uploaded_files:
                    st.warning("Upload at least one PDF.")
                else:
                    with st.spinner("Processing..."):
                        sess      = st.session_state.chat_sessions[active_name]
                        existing  = sess.get("papers", [])
                        new_files = [f for f in uploaded_files if f.name not in existing]

                        if not new_files:
                            st.info("All selected files are already processed.")
                        else:
                            user_id    = st.session_state.get("user_id", "anon")
                            session_id = sess["id"]

                            results    = process_files_parallel(
                                new_files, existing, user_id, session_id
                            )
                            all_chunks = []
                            if "pdf_paths" not in sess:
                                sess["pdf_paths"] = {}

                            for result in results:
                                if result is None:
                                    continue
                                if result[0] == "__error__":
                                    st.error(f"Error with {result[1]}: {result[2]}")
                                    continue
                                name, chunks, analysis, pdf_path = result
                                all_chunks.extend(chunks)
                                sess["analysis"][name]  = analysis
                                sess["papers"].append(name)
                                sess["pdf_paths"][name] = pdf_path

                            if all_chunks:
                                vs = get_vs(active_name)
                                if vs is None:
                                    create_vs(active_name, all_chunks)
                                else:
                                    vs.add_documents(all_chunks)
                                # Invalidate query cache — new paper changes retrieval results
                                st.session_state.pop("query_cache", None)
                                save_state()
                                st.rerun()

    with t_col2:
        model_display_name = st.session_state.selected_model.split()[1]
        with st.popover(f"🧠 {model_display_name}", use_container_width=True):
            chosen_model = st.selectbox(
                "Model", list(MODELS.keys()),
                index=list(MODELS.keys()).index(st.session_state.selected_model),
                label_visibility="collapsed"
            )
            if chosen_model != st.session_state.selected_model:
                st.session_state.selected_model = chosen_model
                # FIX: get_llm is cached by (model_id, api_key) args.
                # Clearing it wipes ALL cached models which is wasteful but safe.
                # The correct approach is to just let the cache serve the new model
                # on the next call — no manual clear needed.
                # Removed the broken `get_llm.clear()` call entirely.
                st.rerun()

    # ── Chat input ────────────────────────────────────────────────────────────
    user_query = st.chat_input("Ask anything about your research papers...")
    if quick_query:
        user_query = quick_query

    if user_query:
        if not active_sess["papers"]:
            st.warning("Upload papers to this chat first using the ➕ button.")
        else:
            active_sess["messages"].append({"role": "user", "content": user_query})

            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                    # FIX #1: stream the response — words appear as generated,
                    # feels much faster. st.write_stream() consumes the generator
                    # and returns the full assembled string when done.
                    with st.spinner("Searching papers..."):
                        # Retrieval happens inside rag_query_stream before
                        # the first chunk is yielded, so spinner covers that.
                        stream   = rag_query_stream(user_query, active_name, selected_paper)
                        answer   = st.write_stream(stream)

                    # After streaming, fetch context docs for the sources expander.
                    # We call the cached non-streaming variant — it returns instantly
                    # from cache since the answer was just stored there by the stream.
                    response = rag_query(user_query, active_name, selected_paper)

                    sources = []
                    if response["context"]:
                        with st.expander("📄 View Sources"):
                            for i, doc in enumerate(response["context"]):
                                paper    = doc.metadata.get("paper_name", "Unknown")
                                page     = doc.metadata.get("page", "")
                                page_str = f" — Page {int(page)+1}" if page != "" else ""
                                label    = f"**Source {i+1}:** `{paper}`{page_str}"
                                snippet  = doc.page_content[:250] + "..."
                                st.markdown(label)
                                st.caption(snippet)
                                sources.append({"label": label, "snippet": snippet})

            active_sess["messages"].append({
                "role":    "assistant",
                "content": answer,
                "sources": sources,
            })
            save_state()
            st.rerun()