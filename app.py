"""
SRE Command Center — Gradio UI

Streaming two-panel interface:
  Left  — SRE analysis that fills in as the agent finishes
  Right — reasoning trace that updates live after each tool call
"""

import queue
import sys
import threading
import types

# audioop removed in Python 3.13+; stub for pydub (Gradio dep), never exercised here.
if "audioop" not in sys.modules:
    sys.modules["audioop"] = types.ModuleType("audioop")

import gradio as gr
from langchain.callbacks.base import BaseCallbackHandler

from agent.core import build_agent

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


# ── Streaming callback ────────────────────────────────────────────────────────

class _QueueCallback(BaseCallbackHandler):
    """Emits tool-start / tool-end / finish events to a Queue."""

    def __init__(self, q: queue.Queue):
        self.q = q

    def on_tool_start(self, serialized, input_str, **_):
        self.q.put(("tool_start", serialized.get("name", "tool"), str(input_str)))

    def on_tool_end(self, output, **_):
        self.q.put(("tool_end", str(output)))

    def on_agent_finish(self, finish, **_):
        self.q.put(("finish", finish.return_values.get("output", "")))

    def on_chain_error(self, error, **_):
        self.q.put(("error", str(error)))

    def on_tool_error(self, error, **_):
        self.q.put(("error", str(error)))


def _run_agent(incident: str, q: queue.Queue):
    try:
        _get_agent().invoke({"input": incident}, {"callbacks": [_QueueCallback(q)]})
    except Exception as e:
        q.put(("error", str(e)))
    finally:
        q.put(("done", None))


# ── Generator function (streams 3 outputs) ───────────────────────────────────

def investigate(incident: str):
    """Yields (analysis, trace, status) tuples as the investigation progresses."""
    if not incident.strip():
        yield "Please describe the incident.", "", "[ READY ]"
        return

    q = queue.Queue()
    thread = threading.Thread(target=_run_agent, args=(incident, q), daemon=True)
    thread.start()

    trace_steps = []
    current_name = None
    current_input = None
    step_num = 0
    analysis = ""

    yield "_Starting investigation..._", "", "[ INVESTIGATING... ]"

    while True:
        try:
            event = q.get(timeout=90)
        except queue.Empty:
            yield "Investigation timed out (90 s).", _render_trace(trace_steps), "[ TIMED OUT ]"
            break

        kind = event[0]

        if kind == "tool_start":
            _, current_name, current_input = event
            step_num += 1
            trace_steps.append(
                f"**Step {step_num} &mdash; `{current_name}`**  \n"
                f"Input: `{current_input}`  \n"
                f"*running...*"
            )
            yield "_Investigating..._", _render_trace(trace_steps), "[ INVESTIGATING... ]"

        elif kind == "tool_end":
            _, output = event
            preview = output[:500] + ("..." if len(output) > 500 else "")
            if trace_steps:
                trace_steps[-1] = (
                    f"**Step {step_num} &mdash; `{current_name}`**  \n"
                    f"Input: `{current_input}`  \n"
                    f"```\n{preview}\n```"
                )
            yield "_Investigating..._", _render_trace(trace_steps), "[ INVESTIGATING... ]"

        elif kind == "finish":
            _, output = event
            analysis = output.strip()
            if not analysis:
                analysis = _fallback_msg(trace_steps)
            yield analysis, _render_trace(trace_steps), "[ DONE ]"
            break

        elif kind == "error":
            _, err = event
            yield f"**Error:** {err}", _render_trace(trace_steps), "[ ERROR ]"
            break

        elif kind == "done":
            if not analysis:
                analysis = _fallback_msg(trace_steps)
                yield analysis, _render_trace(trace_steps), "[ LIMIT REACHED ]"
            break

    thread.join(timeout=2)


def _render_trace(steps: list) -> str:
    return "\n\n---\n\n".join(steps) if steps else ""


def _fallback_msg(steps: list) -> str:
    tools = [s.split("`")[1] for s in steps if "Step" in s and "`" in s]
    return (
        "The agent reached its iteration limit without producing a final answer.\n\n"
        f"**Tools called:** {', '.join(f'`{t}`' for t in tools) or 'none'}\n\n"
        "Try rephrasing with a known service name: `checkout-service`, `inventory-service`."
    )


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
.gradio-container { max-width: 1350px !important; margin: 0 auto; }

/* Header banner */
#sre-header {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 55%, #24243e 100%);
    border-radius: 12px;
    padding: 28px 36px 22px;
    margin-bottom: 16px;
}
#sre-header .prose h1 {
    color: #a78bfa !important;
    font-size: 1.85rem !important;
    margin: 0 0 6px !important;
    letter-spacing: -0.5px;
}
#sre-header .prose p { color: #c4b5fd !important; margin: 0 !important; font-size: 0.9rem !important; }

/* Status badge */
#sre-status .prose p {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 1px;
    background: #1e1b4b;
    color: #a5b4fc;
    border: 1px solid #4338ca;
    margin: 0;
}

/* Input textbox */
#sre-input textarea {
    font-size: 15px !important;
    border-radius: 8px !important;
    min-height: 72px !important;
}

/* Investigate button */
#sre-btn {
    min-height: 72px !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    border-radius: 8px !important;
    background: linear-gradient(135deg, #6d28d9, #4f46e5) !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(99, 102, 241, 0.45) !important;
    transition: box-shadow 0.2s ease, transform 0.15s ease !important;
}
#sre-btn:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.65) !important;
    transform: translateY(-2px) !important;
}

/* Section headings */
.panel-heading .prose h3 {
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    color: #64748b !important;
    margin: 0 0 10px !important;
}

/* Analysis panel */
#sre-analysis {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    padding: 22px 26px !important;
    min-height: 380px !important;
}
#sre-analysis .prose {
    color: #e2e8f0 !important;
    font-size: 0.92rem !important;
    line-height: 1.75 !important;
}
#sre-analysis .prose h1, #sre-analysis .prose h2, #sre-analysis .prose h3 {
    color: #a78bfa !important;
}
#sre-analysis .prose strong { color: #c4b5fd !important; }
#sre-analysis .prose code {
    background: #1e293b !important;
    color: #7dd3fc !important;
    padding: 1px 5px !important;
    border-radius: 4px !important;
}

/* Trace panel */
#sre-trace {
    background: #0a0f1e !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    padding: 18px 20px !important;
    min-height: 380px !important;
}
#sre-trace .prose {
    color: #94a3b8 !important;
    font-size: 0.8rem !important;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace !important;
    line-height: 1.6 !important;
}
#sre-trace .prose strong { color: #7dd3fc !important; }
#sre-trace .prose code  { color: #34d399 !important; background: #0f2d22 !important; padding: 1px 4px !important; border-radius: 3px !important; }
#sre-trace .prose pre  { background: #111827 !important; border-left: 3px solid #334155 !important; padding: 10px 14px !important; border-radius: 6px !important; white-space: pre-wrap !important; word-break: break-word !important; }
#sre-trace .prose hr   { border-color: #1e293b !important; margin: 12px 0 !important; }
"""

# ── Layout ────────────────────────────────────────────────────────────────────

EXAMPLES = [
    ["payments-service has high error rate"],
    ["checkout-service CPU at 94% for the last 10 minutes"],
    ["inventory-service pod is crash-looping"],
    ["database connection pool exhausted on prod"],
]

with gr.Blocks(title="SRE Command Center", css=CSS) as demo:

    gr.Markdown(
        "# SRE Command Center\n"
        "Describe an active incident. The agent calls monitoring tools in real-time and produces a structured investigation report.",
        elem_id="sre-header",
    )

    status_out = gr.Markdown("[ READY ]", elem_id="sre-status")

    with gr.Row(equal_height=True):
        incident_input = gr.Textbox(
            label="Incident Description",
            placeholder="e.g. checkout-service CPU at 94% for the last 10 minutes",
            lines=2,
            scale=5,
            elem_id="sre-input",
        )
        run_btn = gr.Button("Investigate", variant="primary", scale=1, elem_id="sre-btn")

    gr.Examples(examples=EXAMPLES, inputs=incident_input, label="Quick examples")

    with gr.Row(equal_height=False):
        with gr.Column(scale=3):
            gr.Markdown("### SRE Analysis", elem_classes="panel-heading")
            analysis_out = gr.Markdown(
                value="_Analysis will appear here._",
                elem_id="sre-analysis",
            )
        with gr.Column(scale=2):
            gr.Markdown("### Reasoning Trace", elem_classes="panel-heading")
            trace_out = gr.Markdown(
                value="_Tool calls will stream here as the agent works._",
                elem_id="sre-trace",
            )

    outputs = [analysis_out, trace_out, status_out]
    run_btn.click(fn=investigate, inputs=incident_input, outputs=outputs)
    incident_input.submit(fn=investigate, inputs=incident_input, outputs=outputs)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(),
    )
