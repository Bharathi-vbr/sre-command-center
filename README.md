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

---

## Adapting for production

This project uses mock data for the five tools. Replacing each mock with a real integration is the only change needed to make the agent production-ready.

### 1. Wire tools to real data sources

Every tool lives in [`agent/tools.py`](agent/tools.py). Replace the mock return values:

| Tool | Current | Replace with |
|---|---|---|
| `fetch_recent_alerts` | hardcoded alert dicts | PagerDuty API, OpsGenie, or Alertmanager webhook |
| `check_deployment` | hardcoded deploy list | ArgoCD API, Spinnaker, or your CI/CD release endpoint |
| `fetch_metrics` | random numbers | Prometheus `query` API, Datadog metrics API, or CloudWatch |
| `search_runbook` | ChromaDB (already real) | Keep as-is — just add your own runbooks to `data/runbooks/` |
| `search_incidents` | ChromaDB (already real) | Keep as-is — or ingest from PagerDuty incident history |

Example — replacing `fetch_metrics` with a real Prometheus query:

```python
import requests

@tool
def fetch_metrics(service_name: str) -> str:
    """Fetch live CPU, error rate, and p99 latency from Prometheus."""
    base = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
    queries = {
        "cpu": f'rate(container_cpu_usage_seconds_total{{service="{service_name}"}}[5m])',
        "error_rate": f'rate(http_requests_total{{service="{service_name}",status=~"5.."}}[5m])',
        "p99_latency": f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{service_name}"}}[5m]))',
    }
    results = {}
    for metric, query in queries.items():
        r = requests.get(f"{base}/api/v1/query", params={"query": query}, timeout=5)
        results[metric] = r.json()["data"]["result"]
    return str(results)
```

### 2. Add your own runbooks and past incidents

Drop markdown files into `data/runbooks/` and `data/incidents/`. Delete `chroma_db/` and restart — `ingest_all()` rebuilds the vector store automatically.

```bash
# Add a new runbook
echo "# Database replication lag\n\nStep 1: ..." > data/runbooks/db_replication_lag.md

# Rebuild the vector store
rm -rf chroma_db/
python -c "from rag.ingest import ingest_all; ingest_all()"
```

The agent will immediately find and cite it during investigations.

### 3. Swap the LLM

The LLM is set in [`agent/core.py`](agent/core.py). One line change:

```python
# Groq (current — fast, free tier)
from langchain_groq import ChatGroq
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.1)

# OpenAI
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

# Anthropic Claude
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-sonnet-4-5", temperature=0.1)

# Azure OpenAI (for enterprises with data residency requirements)
from langchain_openai import AzureChatOpenAI
llm = AzureChatOpenAI(azure_deployment="gpt-4o", temperature=0.1)
```

### 4. Scale the vector store

ChromaDB runs locally by default. For a shared team deployment, switch to a hosted vector DB:

```python
# rag/store.py — swap the client
import chromadb

# Local (default)
client = chromadb.PersistentClient(path="chroma_db")

# ChromaDB Cloud
client = chromadb.HttpClient(host="your-chroma-host", port=8000)

# Or swap ChromaDB entirely for Pinecone, Weaviate, or pgvector
```

### 5. Deploy internally

**Docker (single container):**
```bash
docker build -t sre-command-center .
docker run -p 7860:7860 \
  -e GROQ_API_KEY=$GROQ_API_KEY \
  -e LANGCHAIN_API_KEY=$LANGCHAIN_API_KEY \
  sre-command-center
```

**Kubernetes (team-shared):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sre-command-center
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: app
        image: your-registry/sre-command-center:latest
        ports:
        - containerPort: 7860
        envFrom:
        - secretRef:
            name: sre-command-center-secrets
```

### 6. Security considerations for production

- **Never log raw tool output** — it may contain secrets, PII, or internal hostnames. LangSmith traces are off by default unless `LANGCHAIN_TRACING_V2=true`.
- **Scope API credentials** — the tool credentials (Prometheus, PagerDuty, etc.) should be read-only service accounts.
- **Network isolation** — run the container inside your VPC; only expose port 7860 behind your internal SSO proxy.
- **Rate-limit the LLM** — set `max_iterations=8` (already done) and wrap the agent in a per-user semaphore to prevent runaway cost from concurrent requests.
