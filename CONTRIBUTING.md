# Contributing

Thanks for your interest in improving SRE Command Center. This guide covers everything you need to get a change merged.

## What to work on

Check the [open issues](https://github.com/Bharathi-vbr/sre-command-center/issues) first. Issues tagged `good first issue` are scoped to a single file. Issues tagged `help wanted` are higher-effort but well-defined.

If you have an idea that isn't tracked yet, open an issue before writing code so we can align on the approach.

## Setup

```bash
git clone https://github.com/Bharathi-vbr/sre-command-center.git
cd sre-command-center
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
```

## Where things live

| File | What to touch |
|---|---|
| `agent/tools.py` | Add or modify a tool the agent can call |
| `agent/prompts.py` | Change how the agent reasons or structures output |
| `agent/core.py` | Change agent settings (iterations, temperature, memory) |
| `rag/ingest.py` | Change how documents are chunked or ingested |
| `data/runbooks/` | Add a new runbook (plain markdown, no special format) |
| `data/incidents/` | Add a past incident for RAG search |
| `app.py` | Change the Gradio UI layout or streaming logic |

## Adding a new tool

1. Write a function decorated with `@tool` in `agent/tools.py`. The docstring is what the LLM reads to decide when to call it — make it precise.
2. Register it in the `tools` list in `agent/core.py`.
3. Test it by running the app locally and triggering an incident that should invoke it.

```python
@tool
def your_new_tool(service_name: str) -> str:
    """One clear sentence describing what this tool does and when to use it."""
    try:
        # your implementation
        return result
    except Exception as e:
        return f"Error: {e}"   # always return a string, never raise
```

## Adding runbooks

Drop a `.md` file in `data/runbooks/`. Delete `chroma_db/` and restart the app — `ingest_all()` rebuilds the vector store on boot.

```bash
echo "# My new runbook\n\nStep 1: ..." > data/runbooks/my_runbook.md
rm -rf chroma_db/
python app.py
```

## Pull request checklist

- [ ] Tested locally — ran the app and triggered the relevant code path
- [ ] Tool docstrings updated if you changed what a tool does
- [ ] No API keys or secrets in the diff
- [ ] `requirements.txt` updated if you added a dependency (`pip freeze > requirements.txt` from inside the venv)
- [ ] PR description explains *why*, not just *what*

## Code style

- No comments unless the *why* is non-obvious
- Tools must handle all exceptions and return an error string — never raise
- `os.getenv()` for all credentials — no hardcoded keys
