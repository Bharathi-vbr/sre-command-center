"""
SRE Agent Core

Builds and returns the LangChain ReAct AgentExecutor for the on-call SRE assistant.
"""

import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq

from agent.tools import (
    check_deployment,
    fetch_recent_alerts,
    fetch_metrics,
    search_incidents,
    search_runbook,
)

load_dotenv()

# Compact ReAct prompt — keeps token count low for the free-tier 6000 TPM limit.
_REACT_TEMPLATE = """You are a production SRE on-call assistant. Use tools to investigate the incident, then produce a structured report.

Tools available:
{tools}

STRICT RULES:
1. Action Input must be a plain string — never key=value syntax.
2. Call tools in this order: fetch_recent_alerts → check_deployment → search_runbook → search_incidents.
3. If a tool returns no results, skip to the next tool immediately. Never repeat the same tool call.
4. You MUST finish with "Final Answer:" regardless of how much data you gathered.

Response format (follow exactly):
Thought: <reasoning>
Action: <tool name from [{tool_names}]>
Action Input: <plain string>
Observation: <tool result>
... repeat steps above as needed ...
Thought: I have enough information to write the report.
Final Answer: SITUATION: ... | ROOT CAUSE: ... | IMMEDIATE STEPS: ... | DIAGNOSTIC COMMANDS: ... | CONFIDENCE: ...

Begin!

Question: {input}
Thought:{agent_scratchpad}"""


def build_agent() -> AgentExecutor:
    """Build and return the SRE on-call ReAct AgentExecutor."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=api_key,
        temperature=0.1,
    )

    tools = [fetch_recent_alerts, search_runbook, check_deployment, search_incidents, fetch_metrics]
    prompt = PromptTemplate.from_template(_REACT_TEMPLATE)
    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    return AgentExecutor(
        agent=agent,
        tools=tools,
        max_iterations=6,
        early_stopping_method="generate",
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )
