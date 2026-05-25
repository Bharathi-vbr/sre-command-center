# SRE Command Center Agent

## What this is
A production-grade SRE on-call assistant. Multi-tool ReAct agent
that investigates incidents by autonomously calling tools:
alert fetcher, runbook search (RAG), deployment checker,
past incident search (RAG), metrics fetcher.

## Stack
- LangChain ReAct agent
- Groq Llama 3 8B (LLM — fast, free tier)
- HuggingFace all-MiniLM-L6-v2 (embeddings — free, local)
- ChromaDB (vector store — local, persisted to disk)
- Gradio (UI)
- Python 3.11

## Key files
- agent/core.py     — AgentExecutor setup, ReAct loop
- agent/tools.py    — all 5 SRE tools the agent can call
- agent/prompts.py  — system prompt with SRE context
- rag/store.py      — ChromaDB read/write wrapper
- rag/ingest.py     — embed runbooks + incidents into vector store
- app.py            — Gradio UI with reasoning trace panel

## Rules when writing code
- Always handle tool errors gracefully — return error string, never raise
- Every tool @decorator must have a clear docstring — the LLM reads it
- Max iterations = 8 in AgentExecutor
- Temperature = 0.1 (consistent structured output)
- Never hardcode API keys — always use os.getenv()
