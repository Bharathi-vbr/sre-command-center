---
title: SRE Command Center Agent
emoji: 🔧
colorFrom: red
colorTo: indigo
sdk: gradio
sdk_version: 6.14.0
app_file: app.py
pinned: true
---

# SRE Command Center

When production breaks at 3 AM, you need answers in seconds — not a checklist to work through manually. Describe the incident in plain English and the agent immediately correlates alerts, deployment history, runbooks, past incidents, and live metrics into a structured investigation report with root cause hypothesis, ranked actions, and exact diagnostic commands to run.

## What the agent does

Given an incident like *"checkout-service CPU at 94% for the last 10 minutes"*, it autonomously:

1. **Fetches active alerts** — filters by service, surfaces severity and timeline
2. **Checks recent deployments** — correlates the spike with any code changes in the last hour
3. **Searches runbooks** — semantic search across remediation procedures to find the relevant playbook
4. **Searches past incidents** — finds similar incidents with known root causes and MTTRs
5. **Pulls live metrics** — CPU, memory, error rate, and p99 latency with baseline comparisons

Output is a structured report: situation → root cause hypothesis (with confidence %) → prioritised immediate steps → copy-paste diagnostic commands → postmortem skeleton.

## Architecture

```
User prompt
    │
    ▼
LangChain ReAct agent (llama-3.1-8b-instant · Groq)
    │
    ├── fetch_recent_alerts   → mock monitoring data, filtered by service
    ├── check_deployment      → recent deploy history with rollback status
    ├── search_runbook        → ChromaDB vector search · 39 runbook chunks
    ├── search_incidents      → ChromaDB vector search · 8 incident chunks
    └── fetch_metrics         → CPU / memory / error rate / latency
            │
            ▼
    Gradio UI — analysis panel + live reasoning trace
```

- **Embeddings:** `all-MiniLM-L6-v2` via ChromaDB's built-in ONNX runtime (no GPU needed)
- **LLM:** Groq-hosted Llama 3.1 8B — fast, free tier, ~2 s to first token
- **Streaming:** LangChain `BaseCallbackHandler` + `queue.Queue` — tool calls appear in the trace panel in real time as the agent works

## Screenshot

![Reasoning trace showing the agent calling fetch_recent_alerts, check_deployment, search_runbook, and fetch_metrics before producing a structured incident report](screenshot.png)

## Setup

Set `GROQ_API_KEY` in the Space secrets (Settings → Variables and secrets). No GPU required.
