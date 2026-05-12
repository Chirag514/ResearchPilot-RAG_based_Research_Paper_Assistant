import os
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from backend.clients import get_llm, call_with_retry_fallback
from backend.storage import upload_pdf
import streamlit as st


# ── System prompt for analysis ─────────────────────────────────────────────────
_ANALYZE_SYSTEM = (
    "Extract from this paper:\n"
    "- **Title & Authors**\n- **Objective**\n- **Methodology**\n"
    "- **Key Findings** (bullets)\n- **Limitations**\n- **Keywords**\n"
    "Be concise. Skip missing sections."
)

def auto_analyze(text: str, paper_name: str) -> str:
    """Analyze paper text using fallback model chain.

    No model_id param — call_with_retry_fallback tries all models in
    ANALYZE_MODEL_CHAIN automatically, starting with the fastest (8B).
    Safe to call from the main thread only (sequential by design).
    """
    def fn_factory(model_id: str, api_key: str):
        _llm   = get_llm(model_id, api_key)
        prompt = ChatPromptTemplate.from_messages(
            [("system", _ANALYZE_SYSTEM), ("human", "{input}")]
        )
        chain  = prompt | _llm | StrOutputParser()
        return lambda inp: chain.invoke(inp)

    return call_with_retry_fallback(
        fn_factory,
        {"input": f"Paper: {paper_name}\n\nText:\n{text[:3000]}"}
    )


def _load_chunk_upload(args) -> tuple:
    """Stage 1 — runs in parallel threads.

    Loads PDF pages, splits into chunks, uploads raw PDF to Supabase.
    Does NOT call the LLM — keeps threads free of Groq API calls so
    we never fire multiple simultaneous requests and hit rate limits.

    Returns: (file_name, chunks, sample_text, pdf_path)
         or: ("__error__", file_name, error_message)
    """
    file, existing_papers, user_id, session_id = args

    if file.name in existing_papers:
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name

        pages = PyPDFLoader(tmp_path).load()
        for page in pages:
            page.metadata["paper_name"] = file.name

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500, chunk_overlap=300,
            separators=[
                "\nAbstract", "\nIntroduction", "\nRelated Work",
                "\nBackground", "\nMethodology", "\nMethod",
                "\nExperiments", "\nResults", "\nDiscussion",
                "\nConclusion", "\nReferences", "\n\n", "\n", ". "
            ]
        )
        chunks  = [c for c in splitter.split_documents(pages) if c.page_content.strip()]
        sample  = " ".join(p.page_content for p in pages[:3])

        # Upload PDF bytes to Supabase Storage (network I/O — fine in thread)
        pdf_path = upload_pdf(user_id, session_id, file.name, file.getvalue())

        return (file.name, chunks, sample, pdf_path)

    except Exception as e:
        return ("__error__", file.name, str(e))

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def process_files_parallel(new_files: list, existing_papers: list,
                            user_id: str, session_id: str) -> list:
    """Two-stage pipeline:

    Stage 1 (parallel)   — load, chunk, upload to Supabase.
                           No LLM calls → no rate limit risk.
    Stage 2 (sequential) — call auto_analyze one paper at a time with a
                           small gap between calls. Uses fallback model
                           chain (8B → Scout → GPT-OSS 20B → Qwen3 →
                           70B → GPT-OSS 120B) so rate limits on one
                           model automatically roll over to the next.

    Returns list of (name, chunks, analysis, pdf_path) tuples,
    plus ("__error__", name, msg) for any failures.
    """
    args = [(f, existing_papers, user_id, session_id) for f in new_files]

    # ── Stage 1: parallel load + chunk + upload ────────────────────────────────
    with ThreadPoolExecutor() as ex:
        stage1_results = list(ex.map(_load_chunk_upload, args))

    # ── Stage 2: sequential LLM analysis ──────────────────────────────────────
    # Collect only the results that will actually trigger an LLM call so the
    # inter-call sleep fires correctly between real analysis calls only.
    analyzable = [
        (i, r) for i, r in enumerate(stage1_results)
        if r is not None and r[0] != "__error__"
    ]

    final_results = [None] * len(stage1_results)

    # Pass through None and error results unchanged
    for i, result in enumerate(stage1_results):
        if result is None or result[0] == "__error__":
            final_results[i] = result

    # Run LLM analysis sequentially with a sleep between calls
    for call_idx, (i, result) in enumerate(analyzable):
        name, chunks, sample, pdf_path = result
        try:
            analysis = auto_analyze(sample, name)
        except Exception as e:
            # All models exhausted — paper is still usable for chat,
            # analysis tab will just show a fallback message
            analysis = (
                f"⚠️ Auto-analysis unavailable (rate limit on all models). "
                f"Paper is fully uploaded and searchable in chat.\n\n"
                f"Error: {str(e)[:200]}"
            )
        final_results[i] = (name, chunks, analysis, pdf_path)

        # Small gap between sequential Groq calls — reduces 429 risk.
        # Only sleep between calls, not after the last one.
        if call_idx < len(analyzable) - 1:
            time.sleep(1)

    return final_results