# 🔬 ResearchPilot — RAG-Based Research Paper Assistant

A multi-user research assistant that lets you upload PDFs and have context-aware conversations with your research papers — with page-level citations, auto paper analysis, and research tools powered by RAG.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36.0-red)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-0.2.16-green)](https://langchain.com)

**[Live Demo](https://researchpilot-rag.streamlit.app/) | [GitHub](https://github.com/Chirag514/ResearchPilot-RAG_based_Research_Paper_Assistant)**
---

## ✨ Features

- **💬 Context-aware Q&A** — Ask questions about your papers and get answers with exact page citations
- **📊 Auto Paper Analysis** — Automatically extracts title, authors, objectives, methodology, findings, limitations, and keywords
- **📄 PDF Viewer** — View papers directly in the app with download and open-in-tab options
- **🛠️ 4 Research Tools:**
  - Quiz Generator — generate quiz questions with answers and page sources
  - Statistics Extractor — extract all numbers, metrics, and percentages
  - Research Gap Finder — identify open problems from limitations sections
  - Paper Comparator — compare two papers on methodology, results, contributions, etc.
- **🧠 6 Switchable LLMs** — Switch models mid-chat based on speed or quality needs
- **💬 Multi-session Chats** — Create, rename, and delete chat sessions with persistent history
- **🔍 Query Scope** — Filter queries to a specific paper or search across all uploaded papers
- **⚡ Quick Actions** — One-click summaries, methodology, findings, and limitations

---

## 🏗️ Architecture

```
User
 │
 ▼
Streamlit Frontend
 ├── Chat Tab          → RAG Q&A with streaming
 ├── Analysis Tab      → Auto-extracted paper summaries
 ├── PDF Viewer Tab    → Signed URL iframe viewer
 └── Tools Tab         → Research tools
 │
 ▼
Backend
 ├── pdf_processor.py  → Two-stage pipeline (parallel I/O + sequential LLM)
 ├── rag.py            → MMR retrieval + streaming + LRU cache
 ├── vector_store.py   → Per-user Pinecone namespaces
 ├── storage.py        → Private Supabase Storage + signed URLs
 └── state.py          → Persistent chat state via Supabase DB
 │
 ├── Pinecone          → Vector storage (all-MiniLM-L6-v2 embeddings)
 ├── Groq API          → LLM inference (6 models with fallback chain)
 └── Supabase          → Auth + DB + Storage
```

---

## 🤖 Supported Models

| Model | Speed | Best For |
|-------|-------|----------|
| ⚡ LLaMA 3.1 8B | Fastest | Quick questions |
| 🧠 LLaMA 3.3 70B | Balanced | Default — best quality |
| 🔭 LLaMA 4 Scout | Fast | Multimodal tasks |
| 💎 GPT-OSS 120B | Slowest | Most complex queries |
| 🚀 GPT-OSS 20B | Balanced | Good quality/speed tradeoff |
| 🌐 Qwen3 32B | Balanced | Multilingual papers |

---

## ⚙️ Technical Highlights

- **Two-stage PDF pipeline** — parallel load/chunk/upload + sequential LLM analysis with 6-model fallback chain, reducing auto-analysis failure rate from **74% → ~0%** across 1,155 LangSmith traced runs
- **MMR-based retrieval** — Maximal Marginal Relevance for diverse, non-redundant context chunks at ~0.52s median retrieval
- **Token-by-token streaming** — responses appear word-by-word for perceived instant feedback
- **LRU query cache** — 50-entry cache eliminates redundant Pinecone + Groq calls for repeated queries
- **Exponential backoff retry** — handles Groq 429 rate limit errors with `base_delay=5s` up to 4 retries
- **LangSmith observability** — full trace visibility across all LangChain components

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- [Groq API Key](https://console.groq.com)
- [Pinecone API Key](https://pinecone.io)
- [Supabase Project](https://supabase.com) (URL + anon key + service role key)

### Installation

```bash
# Clone the repo
git clone https://github.com/Chirag514/ResearchPilot-RAG_based_Research_Paper_Assistant.git researchpilot
cd researchpilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
PINECONE_API_KEY=your_pinecone_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# Optional — LangSmith tracing (set false for production)
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=ResearchPilot
```

### Supabase Setup

**1. Create `chat_state` table:**
```sql
CREATE TABLE chat_state (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**2. Enable Row Level Security:**
```sql
ALTER TABLE chat_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own state"
ON chat_state FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "Users insert own state"
ON chat_state FOR INSERT
WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users update own state"
ON chat_state FOR UPDATE
USING (user_id = auth.uid());
```

**3. Create private storage bucket:**
- Go to Storage → New Bucket → Name: `pdfs` → **uncheck Public**

### Run the App

```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
researchpilot/
├── app.py                  # Entry point
├── config.py               # Model config
├── requirements.txt
├── .env                    # Environment variables (not committed)
├── backend/
│   ├── auth.py             # Supabase auth (sign in/up/out)
│   ├── clients.py          # API clients + retry utilities
│   ├── pdf_processor.py    # Two-stage PDF pipeline
│   ├── rag.py              # RAG query + streaming + cache
│   ├── state.py            # Persistent state management
│   ├── storage.py          # Supabase Storage operations
│   └── vector_store.py     # Pinecone vector operations
└── frontend/
    ├── theme.py            # UI theme (dark/light/system)
    ├── auth_page.py        # Login/signup page
    ├── sidebar.py          # Session management + quick actions
    └── tabs/
        ├── chat_tab.py     # Chat interface
        └── other_tabs.py   # Analysis, PDF viewer, tools
```

---

## 🔒 Security

- **Private Supabase Storage** — PDFs stored with 6-hour signed URLs, never publicly accessible
- **Row Level Security** — users can only access their own chat state
- **Per-user Pinecone namespaces** — vector isolation between users
- **Service role key** — used server-side only, never exposed to client
