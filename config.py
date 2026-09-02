PINECONE_INDEX = "ragbasedproject"

MODEL_CHAIN = [
    ("💎 GPT-OSS 120B (Most Powerful)",       "groq",   "openai/gpt-oss-120b"),
    ("✨ Gemini 3.7 Flash (High Quality)",     "gemini", "gemini-3.7-flash"),
    ("🚀 GPT-OSS 20B (Balanced)",             "groq",   "openai/gpt-oss-20b"),
    ("⚡ Gemini 3.1 Flash-Lite (High Volume)", "gemini", "gemini-3.1-flash-lite"),
    ("🌊 Gemini 3.5 Flash-Lite (High Volume)", "gemini", "gemini-3.5-flash-lite"),
    ("🔮 Qwen3.8 27B (Good Quality)",          "groq",   "qwen/qwen3.8-27b"),
]
# dropped: qwen/qwen3-32b, all llama models — deprecated, no longer served by Groq

MODELS = {name: (provider, model_id) for name, provider, model_id in MODEL_CHAIN}
