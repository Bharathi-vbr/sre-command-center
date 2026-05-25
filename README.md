# SRE Command Center

**A production-style SRE on-call agent that investigates incidents autonomously in under 60 seconds.**

Describe an incident in plain English. The agent calls five monitoring tools, correlates the results, and returns a structured report with root cause hypothesis, ranked immediate actions, diagnostic commands, and a postmortem skeleton — all without you touching a single dashboard.

**Live demo:** [huggingface.co/spaces/Bharathibhummi/sre-command-center](https://huggingface.co/spaces/Bharathibhummi/sre-command-center)

---

## What the agent does

Given an incident like *"checkout-service CPU at 94% for the last 10 minutes"*, it autonomously:

1. **Fetches active alerts** — filters by service, surfaces severity and timeline
2. **Checks recent deployments** — correlates the spike with any code changes in the past hour
3. **Searches runbooks** — semantic vector search across remediation procedures to find the relevant playbook
4. **Searches past incidents** — finds similar incidents with known root causes and MTTRs
5. **Pulls live metrics** — CPU, memory, error rate, and p99 latency with baseline comparisons

Output is a structured report:
> Situation → Root cause hypothesis (with confidence %) → Prioritised immediate steps → Copy-paste diagnostic commands → Postmortem skeleton

---

## Architecture

```
User prompt
    │
    ▼
LangChain ReAct agent  (Groq · llama-3.1-8b-instant)
    │
    ├── fetch_recent_alerts   →  mock monitoring data, filtered by service
    ├── check_deployment      →  recent deploy history + rollback status
    ├── search_runbook        →  ChromaDB vector search · 39 runbook chunks
    ├── search_incidents      →  ChromaDB vector search · 8 incident chunks
    └── fetch_metrics         →  CPU / memory / error rate / latency
            │
            ▼
    Gradio UI — analysis panel + live reasoning trace
```

---

## Stack

| Layer | Technology |
|---|---|
| LLM | Groq-hosted Llama 3.1 8B — ~2 s to first token, free tier |
| Agent framework | LangChain ReAct (`AgentExecutor`, max 8 iterations) |
| Embeddings | `all-MiniLM-L6-v2` via ChromaDB built-in ONNX runtime (no GPU needed) |
| Vector store | ChromaDB — local, persisted, rebuilt from markdown on cold start |
| UI | Gradio 6 — two-panel streaming layout |
| Observability | LangSmith — full trace of every agent run |
| Deployment | HuggingFace Spaces (free tier) |

---

## Local setup

```bash
# 1. Clone
git clone https://github.com/Bharathi-vbr/sre-command-center.git
cd sre-command-center

# 2. Create virtualenv
python -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Fill in GROQ_API_KEY (required)
# Fill in LANGCHAIN_API_KEY if you want LangSmith tracing (optional)

# 5. Run
python app.py
# → http://localhost:7860
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | [console.groq.com](https://console.groq.com) — free tier is sufficient |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | From [smith.langchain.com](https://smith.langchain.com) |
| `LANGCHAIN_PROJECT` | No | Project name in LangSmith (e.g. `sre-command-center`) |

---

## Project structure

```
sre-command-center/
├── agent/
│   ├── core.py        # AgentExecutor setup, ReAct loop
│   ├── tools.py       # All 5 SRE tools the agent can call
│   └── prompts.py     # System prompt with SRE context
├── rag/
│   ├── store.py       # ChromaDB read/write wrapper
│   └── ingest.py      # Embed runbooks + incidents into vector store
├── data/
│   ├── runbooks/      # Markdown runbooks (high_cpu, high_error_rate, pod_crashloop)
│   └── incidents/     # Past incident reports for RAG search
├── app.py             # Gradio UI with streaming reasoning trace panel
└── requirements.txt
```

---

## LangSmith tracing

Every agent run is traced end-to-end: LLM calls, tool inputs/outputs, token usage, and latency per step.
<img width="1438" height="655" alt="Screenshot 2026-05-25 at 4 20 22 PM" src="https://github.com/user-attachments/assets/a1f4fc22-4b65-4b01-afdf-61787532db36" />


---

## HuggingFace deployment

The app runs on HuggingFace Spaces with a cold-start ingest pattern:

- `chroma_db/` is excluded from git (binary files rejected by HF Spaces)
- On first boot, `ingest_all()` builds the vector store from the markdown files in `data/`
- A skip guard prevents re-ingestion on subsequent restarts

To deploy your own copy:
1. Fork this repo
2. Create a new HuggingFace Space (Gradio SDK)
3. Push the code to the Space remote
4. Add `GROQ_API_KEY` as a Space secret (Settings → Variables and secrets)
