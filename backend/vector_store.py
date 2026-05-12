import streamlit as st
from langchain_pinecone import PineconeVectorStore
from backend.clients import get_embeddings, get_pinecone_client
from config import PINECONE_INDEX


def _namespace(session_name: str) -> str:
    """Prefix session ID with user ID so each user's vectors are isolated."""
    uid = st.session_state.get("user_id", "anon")
    # FIX: guard KeyError — session may have been deleted before this runs
    sessions = st.session_state.get("chat_sessions", {})
    sess = sessions.get(session_name)
    if sess is None:
        # Fallback: use session name hash so we get a stable namespace
        # even if the session dict entry is gone (e.g. during deletion cleanup)
        return f"{str(uid)[:8]}_{session_name}"
    return f"{str(uid)[:8]}_{sess['id']}"


def get_vs(session_name: str):
    """Return the PineconeVectorStore for *session_name*, or None if no
    vectors have been uploaded to this session yet.

    Distinguishes between:
      - Never seen before  → returns None  (chat_tab uses create_vs)
      - Seen + has vectors → returns store (chat_tab uses add_documents)
      - Seen but errored   → returns None
    """
    # Defensive init — in case session_state was partially reset
    if "vector_stores" not in st.session_state:
        st.session_state.vector_stores = {}

    # Key is present → already initialised (may be None on error)
    if session_name in st.session_state.vector_stores:
        return st.session_state.vector_stores.get(session_name)

    # Not yet seen in this process run.  Only build a store object if the
    # session already has papers — otherwise return None so the first upload
    # goes through create_vs (PineconeVectorStore.from_documents), which is
    # a proper bulk upsert rather than an empty store + add_documents.
    sessions = st.session_state.get("chat_sessions", {})
    sess     = sessions.get(session_name, {})
    has_papers = bool(sess.get("papers"))

    if not has_papers:
        # Don't cache None here — let create_vs register the store after
        # the first upload so subsequent uploads use add_documents.
        return None

    ns = _namespace(session_name)
    try:
        vs = PineconeVectorStore(
            index_name=PINECONE_INDEX,
            embedding=get_embeddings(),
            namespace=ns
        )
        st.session_state.vector_stores[session_name] = vs
    except Exception:
        st.session_state.vector_stores[session_name] = None
    return st.session_state.vector_stores.get(session_name)


def create_vs(session_name: str, chunks):
    ns = _namespace(session_name)
    vs = PineconeVectorStore.from_documents(
        chunks,
        embedding=get_embeddings(),
        index_name=PINECONE_INDEX,
        namespace=ns
    )
    st.session_state.vector_stores[session_name] = vs
    return vs


def delete_session_namespace(session_name: str):
    """Delete all vectors for a session from Pinecone."""
    ns = _namespace(session_name)
    try:
        pc    = get_pinecone_client()
        index = pc.Index(PINECONE_INDEX)
        index.delete(delete_all=True, namespace=ns)
    except Exception:
        pass
    st.session_state.vector_stores.pop(session_name, None)


def delete_paper_vectors(session_name: str, paper_name: str):
    """Delete vectors for a single paper from Pinecone namespace."""
    ns = _namespace(session_name)
    try:
        pc    = get_pinecone_client()
        index = pc.Index(PINECONE_INDEX)
        index.delete(
            filter={"paper_name": {"$eq": paper_name}},
            namespace=ns
        )
        st.session_state.vector_stores.pop(session_name, None)
    except Exception as e:
        st.warning(f"⚠️ Could not delete vectors for '{paper_name}': {e}")