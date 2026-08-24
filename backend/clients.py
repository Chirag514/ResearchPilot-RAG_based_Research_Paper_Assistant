import os
import time
import random
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from pinecone import Pinecone, ServerlessSpec
from supabase import create_client
from config import MODELS, MODEL_CHAIN, PINECONE_INDEX

# ── Analyze model fallback chain ───────────────────────────────────────────────
# Derived directly from config.MODEL_CHAIN — same models, same quality order,
# as the manual dropdown. Single source of truth, no drift between the two.
ANALYZE_MODEL_CHAIN = [(provider, model_id) for _, provider, model_id in MODEL_CHAIN]


def _is_rate_limit_error(e: Exception) -> bool:
    msg = str(e).lower()
    return (
        "429" in msg or "rate_limit" in msg or "rate limit" in msg
        or "resource_exhausted" in msg or "resource exhausted" in msg
        or "quota" in msg
    )



def call_with_retry(fn, *args, max_retries: int = 4, base_delay: float = 5.0, **kwargs):
    """Retry fn with exponential backoff on rate-limit errors (Groq 429 or
    Gemini RESOURCE_EXHAUSTED). All other exceptions are re-raised immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            if not _is_rate_limit_error(e) or attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)


def call_with_retry_fallback(fn_factory, *args,
                              max_retries: int = 3, base_delay: float = 5.0,
                              **kwargs):
    """Try each (provider, model_id) in ANALYZE_MODEL_CHAIN, falling back on
    rate-limit exhaustion.

    fn_factory(provider, model_id) must return a callable that accepts *args.
    Falls back to the next model only after exhausting retries for the current one.
    Raises the last error if every model in the chain is exhausted.
    """
    last_error = None

    for provider, model_id in ANALYZE_MODEL_CHAIN:
        fn = fn_factory(provider, model_id)
        for attempt in range(max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if not _is_rate_limit_error(e):
                    raise          # non-rate-limit — don't retry or fallback
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
                else:
                    last_error = e
                    break          # exhausted retries → try next model

    raise last_error               # every model in the chain exhausted


@st.cache_resource(show_spinner=False)
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


@st.cache_resource(show_spinner=False)
def get_pinecone_client():
    pc       = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    existing = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX not in existing:
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
    return pc


@st.cache_resource(show_spinner=False)
def get_supabase():
    """Anon client — used for Auth (sign in / sign up) only."""
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )


@st.cache_resource(show_spinner=False)
def get_supabase_admin():
    """Service role client — used for DB and Storage operations.
    Bypasses RLS so server-side reads/writes always work."""
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )


@st.cache_resource(show_spinner=False)
def get_llm(provider: str, model_id: str):
    """Cached per (provider, model_id) — Streamlit hashes the args automatically."""
    if provider == "groq":
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model=model_id,
            temperature=0
        )
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(
            google_api_key=os.getenv("GEMINI_API_KEY"),
            model=model_id,
            temperature=0
        )
    raise ValueError(f"Unknown provider: {provider}")


def llm():
    provider, model_id = MODELS[st.session_state.selected_model]
    return get_llm(provider, model_id)
