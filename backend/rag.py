import streamlit as st
from concurrent.futures import ThreadPoolExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.clients import llm, call_with_retry
from backend.vector_store import get_vs
    
# ── Query cache ────────────────────────────────────────────────────────────────
# Keyed by (session_name, paper_filter, question) — cleared when a new paper is
# added (handled in chat_tab.py by popping "query_cache" on successful upload).
_CACHE_MAX = 50  # max entries before oldest are evicted


def _cache_get(key: str):
    cache = st.session_state.get("query_cache", {})
    return cache.get(key)


def _cache_set(key: str, value: dict):
    if "query_cache" not in st.session_state:
        st.session_state.query_cache = {}
    cache = st.session_state.query_cache
    # Evict oldest entry if over limit
    if len(cache) >= _CACHE_MAX:
        oldest = next(iter(cache))
        del cache[oldest]
    cache[key] = value


# ── Helpers ────────────────────────────────────────────────────────────────────
def format_docs(docs) -> str:
    parts = []
    for doc in docs:
        paper    = doc.metadata.get("paper_name", "Unknown")
        page     = doc.metadata.get("page", "")
        page_str = f", Page {int(page)+1}" if page != "" else ""
        content  = doc.page_content.replace("{", "{{").replace("}", "}}")
        parts.append(f"[Paper: {paper}{page_str}]\n{content}")
    return "\n\n".join(parts)


def retrieve_for_paper(vs, paper_name: str, question: str, k: int = 4):
    """vs passed explicitly — safe to call from threads."""
    if vs is None:
        return []
    retriever = vs.as_retriever(
        search_type="mmr",
        search_kwargs={
            # FIX #7: reduced fetch_k from 15 → 10 to lower Pinecone latency;
            # still enough candidates for MMR diversity.
            "k": k, "fetch_k": 10, "lambda_mult": 0.7,
            "filter": {"paper_name": {"$eq": paper_name}}
        }
    )
    return retriever.invoke(question)


def _build_history_messages(messages: list) -> list:
    """Return last 2 Q&A exchanges as LangChain message tuples.

    Rate-limit guard: only included when the chat is short (≤ 20 messages)
    AND the last 4 messages are under a combined ~600-token budget (~2400 chars).
    Returns [] (no history) if either guard triggers.
    """
    if not messages or len(messages) > 20:
        return []

    # Grab last 4 messages = 2 human + 2 assistant (may be fewer)
    recent = [m for m in messages if m["role"] in ("user", "assistant")][-4:]
    if not recent:
        return []

    # Token guard: ~4 chars ≈ 1 token; 600 token budget = 2400 chars
    combined = "".join(m["content"] for m in recent)
    if len(combined) > 2400:
        return []

    result = []
    for m in recent:
        role = "human" if m["role"] == "user" else "assistant"
        result.append((role, m["content"]))
    return result


# ── Main query (non-streaming) ─────────────────────────────────────────────────
def rag_query(question: str, session_name: str, paper_filter: str = "🔍 All Papers") -> dict:
    sess   = st.session_state.chat_sessions[session_name]
    papers = sess.get("papers", [])

    if not papers:
        return {"answer": "No papers uploaded in this chat yet.", "context": []}

    # ── Cache check ────────────────────────────────────────────────────────────
    cache_key = f"{session_name}::{paper_filter}::{question}"
    cached    = _cache_get(cache_key)
    if cached:
        return cached

    # ── Retrieval ──────────────────────────────────────────────────────────────
    vs = get_vs(session_name)  # must happen in main thread

    if paper_filter == "🔍 All Papers" and len(papers) > 1:
        def fetch(p):
            docs = retrieve_for_paper(vs, p, question, k=4)
            if not docs:
                return None, None
            block = f"=== {p} ===\n" + format_docs(docs)
            return docs, block

        all_docs, paper_blocks = [], []
        with ThreadPoolExecutor() as ex:
            for docs, block in ex.map(fetch, papers):
                if docs:
                    all_docs.extend(docs)
                    paper_blocks.append(block)

        context = "\n\n".join(paper_blocks)
        system  = (
            "You are an expert research paper assistant. "
            "You have been given context from MULTIPLE research papers. "
            "Answer the question by going through EACH paper one by one. "
            "Use this structure for every paper:\n"
            "**[Paper Name]**\n"
            "[Your answer for this paper with page citations]\n\n"
            "Then end with a **Summary / Comparison** section if relevant. "
            "Always cite exact page numbers. Do NOT skip any paper. "
            "Answer ONLY from the provided context.\n\n"
            f"Context:\n{context}"
        )
    else:
        target   = paper_filter if paper_filter != "🔍 All Papers" else papers[0]
        all_docs = retrieve_for_paper(vs, target, question, k=6)
        context  = format_docs(all_docs)
        system   = (
            "You are an expert research paper assistant. "
            "Each context piece is tagged [Paper: filename, Page X]. "
            "ALWAYS cite the exact paper name and page in your answer. "
            "Answer ONLY from context. No outside knowledge. "
            "If not found: 'This information is not in the provided papers.'\n\n"
            f"Context:\n{context}"
        )

    # ── Build prompt — inject chat history for follow-up awareness ─────────────
    # FIX #5: include last 2 exchanges so "explain further" type questions work.
    # Guarded by length + token budget to avoid rate-limit blowup.
    history  = _build_history_messages(sess.get("messages", []))
    messages = [("system", system)] + history + [("human", "{input}")]
    prompt   = ChatPromptTemplate.from_messages(messages)

    # FIX #8: wrap LLM call with retry for Groq 429 rate-limit errors
    _llm   = llm()  # resolve in main thread
    chain  = prompt | _llm | StrOutputParser()
    answer = call_with_retry(chain.invoke, {"input": question})

    result = {"answer": answer, "context": all_docs}
    _cache_set(cache_key, result)
    return result


# ── Streaming variant ──────────────────────────────────────────────────────────
def rag_query_stream(question: str, session_name: str, paper_filter: str = "🔍 All Papers"):
    """Generator — yields answer chunks. Used by chat_tab.py with st.write_stream().

    Cache: on a cache hit the full answer is yielded as one chunk so the
    caller (st.write_stream) still works correctly.
    No retry wrapper needed — streaming failures surface immediately to the user.
    """
    sess   = st.session_state.chat_sessions[session_name]
    papers = sess.get("papers", [])

    if not papers:
        yield "No papers uploaded in this chat yet."
        return

    # ── Cache hit — yield stored answer directly ───────────────────────────────
    cache_key = f"{session_name}::{paper_filter}::{question}"
    cached    = _cache_get(cache_key)
    if cached:
        yield cached["answer"]
        return

    # ── Retrieval (same logic as rag_query) ────────────────────────────────────
    vs = get_vs(session_name)

    if paper_filter == "🔍 All Papers" and len(papers) > 1:
        def fetch(p):
            docs = retrieve_for_paper(vs, p, question, k=4)
            if not docs:
                return None, None
            block = f"=== {p} ===\n" + format_docs(docs)
            return docs, block

        all_docs, paper_blocks = [], []
        with ThreadPoolExecutor() as ex:
            for docs, block in ex.map(fetch, papers):
                if docs:
                    all_docs.extend(docs)
                    paper_blocks.append(block)

        context = "\n\n".join(paper_blocks)
        system  = (
            "You are an expert research paper assistant. "
            "You have been given context from MULTIPLE research papers. "
            "Answer the question by going through EACH paper one by one. "
            "Use this structure for every paper:\n"
            "**[Paper Name]**\n"
            "[Your answer for this paper with page citations]\n\n"
            "Then end with a **Summary / Comparison** section if relevant. "
            "Always cite exact page numbers. Do NOT skip any paper. "
            "Answer ONLY from the provided context.\n\n"
            f"Context:\n{context}"
        )
    else:
        target   = paper_filter if paper_filter != "🔍 All Papers" else papers[0]
        all_docs = retrieve_for_paper(vs, target, question, k=6)
        context  = format_docs(all_docs)
        system   = (
            "You are an expert research paper assistant. "
            "Each context piece is tagged [Paper: filename, Page X]. "
            "ALWAYS cite the exact paper name and page in your answer. "
            "Answer ONLY from context. No outside knowledge. "
            "If not found: 'This information is not in the provided papers.'\n\n"
            f"Context:\n{context}"
        )

    history  = _build_history_messages(sess.get("messages", []))
    messages = [("system", system)] + history + [("human", "{input}")]
    prompt   = ChatPromptTemplate.from_messages(messages)
    _llm     = llm()
    chain    = prompt | _llm | StrOutputParser()

    # Pre-populate the cache with the context docs BEFORE streaming starts.
    # If streaming fails mid-way the cache entry will have an empty answer
    # string, which is safe — rag_query will re-use context but re-run the
    # LLM rather than serving a partial answer.  Once streaming completes
    # successfully the full answer overwrites the placeholder.
    _cache_set(cache_key, {"answer": "", "context": all_docs})

    # Stream chunks, accumulate full answer for cache
    full_answer = ""
    for chunk in chain.stream({"input": question}):
        full_answer += chunk
        yield chunk

    _cache_set(cache_key, {"answer": full_answer, "context": all_docs})