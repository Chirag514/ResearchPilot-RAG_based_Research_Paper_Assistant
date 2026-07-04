import os
import time
import random
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from pinecone import Pinecone, ServerlessSpec
from supabase import create_client
from config import MODELS, PINECONE_INDEX

# ── Analyze model fallback chain ───────────────────────────────────────────────
# All models from config ordered by preference for background analysis:
# fastest / highest token-limit first, most powerful as final fallback.
ANALYZE_MODEL_CHAIN = [
    "openai/gpt-oss-20b",      # primary
    "qwen/qwen3.6-27b",        # fallback 1
    "qwen/qwen3-32b",          # fallback 2
    "groq/compound-mini",      # fallback 3 (fast)
    "groq/compound",           # fallback 4 (stronger)
    "openai/gpt-oss-120b",     # final fallback (best reasoning)
]


def call_with_retry(fn, *args, max_retries: int = 4, base_delay: float = 5.0, **kwargs):
    """Retry fn with exponential backoff on Groq 429 rate-limit errors.
    All other exceptions are re-raised immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = "429" in msg or "rate_limit" in msg or "rate limit" in msg
            if not is_rate_limit or attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)


def call_with_retry_fallback(fn_factory, *args,
                              max_retries: int = 3, base_delay: float = 5.0,
                              **kwargs):
    """Try each model in ANALYZE_MODEL_CHAIN, falling back on 429 exhaustion.

    fn_factory(model_id, api_key) must return a callable that accepts *args.
    Falls back to the next model only after exhausting retries for the current one.
    Raises the last error if ALL models in the chain are exhausted.
    """
    last_error = None
    groq_key   = os.getenv("GROQ_API_KEY")

    for model_id in ANALYZE_MODEL_CHAIN:
        fn = fn_factory(model_id, groq_key)
        for attempt in range(max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                msg = str(e).lower()
                is_rate_limit = "429" in msg or "rate_limit" in msg or "rate limit" in msg
                if not is_rate_limit:
                    raise          # non-rate-limit — don't retry or fallback
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
                else:
                    last_error = e
                    break          # exhausted retries → try next model

    raise last_error               # all 6 models exhausted


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
def get_llm(model_id: str, api_key: str):
    return ChatGroq(api_key=api_key, model=model_id, temperature=0)


def llm():
    return get_llm(
        MODELS[st.session_state.selected_model],
        os.getenv("GROQ_API_KEY")
    )
