"""
SRE Agent Tools

Five LangChain tools for the on-call SRE ReAct agent.
Each tool builds a structured result dict and returns
json.dumps(result, indent=2)[:2000] — consistent shape,
self-describing keys, and a hard 2000-char token cap.
"""

import json
from datetime import datetime, timedelta, timezone

from langchain.tools import tool

from rag.store import get_store, get_or_create_collection, search_documents


@tool
def fetch_recent_alerts(service_filter: str = "") -> str:
    """Fetch active alerts. Input: a service name to filter by (e.g. checkout-service), or empty string for all alerts. Pass the plain service name only."""
    try:
        now = datetime.now(timezone.utc)
        alerts = [
            {
                "alert_name": "HighCPUUsage",
                "severity": "critical",
                "service": "checkout-service",
                "description": "CPU 94% sustained 8+ min on checkout-service pod-7d4f9",
                "started_at": (now - timedelta(minutes=12)).isoformat(),
            },
            {
                "alert_name": "HighErrorRate",
                "severity": "critical",
                "service": "checkout-service",
                "description": "HTTP 5xx error rate 23% on /api/checkout (threshold: 1%)",
                "started_at": (now - timedelta(minutes=10)).isoformat(),
            },
            {
                "alert_name": "PodCrashLooping",
                "severity": "warning",
                "service": "inventory-service",
                "description": "inventory-service-6b8c4d-xkj9p restarted 5x in last 15 min",
                "started_at": (now - timedelta(minutes=8)).isoformat(),
            },
            {
                "alert_name": "DatabaseLatencyHigh",
                "severity": "warning",
                "service": "checkout-service",
                "description": "PostgreSQL p99 latency 3.2s (threshold: 500ms)",
                "started_at": (now - timedelta(minutes=14)).isoformat(),
            },
        ]

        if service_filter:
            alerts = [a for a in alerts if service_filter.lower() in a["service"].lower()]

        result = {
            "count": len(alerts),
            "service_filter": service_filter or "all",
            "alerts": alerts,
        }
        if not alerts:
            result["message"] = f"No active alerts for service filter '{service_filter}'"

        return json.dumps(result, indent=2)[:2000]
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_runbook(query: str) -> str:
    """Search runbooks for troubleshooting procedures. Input: plain natural-language description of the problem (e.g. high cpu kubernetes node). Returns ranked runbook sections."""
    try:
        store = get_store()
        collection = get_or_create_collection(store, "runbooks")

        if collection.count() == 0:
            return json.dumps({"error": "Runbook database is empty. Run 'python rag/ingest.py' first."})

        results = search_documents(collection, query, n_results=3)
        if not results:
            return json.dumps({"query": query, "results": [], "message": "No relevant runbooks found."})

        result = {
            "query": query,
            "results": [
                {
                    "source": r["metadata"].get("source", "unknown"),
                    "relevance_pct": max(0, int((1 - r.get("distance", 1.0)) * 100)),
                    "content": r["document"][:400],
                }
                for r in results
            ],
        }
        return json.dumps(result, indent=2)[:2000]
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def check_deployment(service: str = "") -> str:
    """Check recent deployments. Input: a service name to filter (e.g. checkout-service), or empty string for all services. Pass the plain service name only."""
    try:
        now = datetime.now(timezone.utc)
        deployments = [
            {
                "service": "checkout-service",
                "version": "v2.14.3",
                "deployed_ago_min": 18,
                "deployed_by": "ci-bot (PR #2341)",
                "status": "deployed",
                "rollback_available": True,
                "changes_summary": "Payment module refactor: async connection handling, new retry logic",
            },
            {
                "service": "inventory-service",
                "version": "v1.9.1",
                "deployed_ago_min": 125,
                "deployed_by": "ci-bot (PR #2338)",
                "status": "deployed",
                "rollback_available": True,
                "changes_summary": "Cache TTL adjusted from 60s to 300s for product catalog",
            },
            {
                "service": "auth-service",
                "version": "v3.2.0",
                "deployed_ago_min": 300,
                "deployed_by": "ci-bot (PR #2330)",
                "status": "deployed",
                "rollback_available": True,
                "changes_summary": "JWT token expiry bumped from 1h to 24h per product request",
            },
        ]

        if service:
            deployments = [d for d in deployments if service.lower() in d["service"].lower()]

        result = {
            "count": len(deployments),
            "service_filter": service or "all",
            "deployments": deployments,
        }
        if not deployments:
            result["message"] = f"No recent deployments for service '{service}'"

        return json.dumps(result, indent=2)[:2000]
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_incidents(query: str) -> str:
    """Search past incidents for similar patterns and root causes. Input: plain natural-language description of the current issue (e.g. high error rate checkout service). Returns similar past incidents."""
    try:
        store = get_store()
        collection = get_or_create_collection(store, "incidents")

        if collection.count() == 0:
            return json.dumps({"error": "Incident database is empty. Run 'python rag/ingest.py' first."})

        results = search_documents(collection, query, n_results=3)
        if not results:
            return json.dumps({"query": query, "results": [], "message": "No similar past incidents found."})

        result = {
            "query": query,
            "results": [
                {
                    "source": r["metadata"].get("source", "unknown"),
                    "similarity_pct": max(0, int((1 - r.get("distance", 1.0)) * 100)),
                    "content": r["document"][:400],
                }
                for r in results
            ],
        }
        return json.dumps(result, indent=2)[:2000]
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def fetch_metrics(service: str, metric: str = "cpu,memory,error_rate,latency") -> str:
    """Fetch metrics for a service. Input: the service name (e.g. checkout-service). Use the metric parameter for specific metrics: cpu, memory, error_rate, latency (comma-separated). Always pass just the service name as the main input."""
    try:
        now = datetime.now(timezone.utc)
        requested = {m.strip().lower() for m in metric.split(",")}

        all_metrics = {
            "cpu": {
                "name": "CPU Utilization",
                "unit": "%",
                "status": "CRITICAL",
                "current": 94,
                "baseline": 35,
                "threshold": 80,
                "p5m_avg": 91,
                "p15m_avg": 78,
                "p1h_avg": 42,
                "spike_started_at": (now - timedelta(minutes=14)).isoformat(),
            },
            "memory": {
                "name": "Memory Usage",
                "unit": "%",
                "status": "OK",
                "current": 71,
                "baseline": 62,
                "threshold": 85,
                "p5m_avg": 70,
                "p15m_avg": 68,
                "p1h_avg": 63,
                "spike_started_at": None,
            },
            "error_rate": {
                "name": "HTTP 5xx Error Rate",
                "unit": "%",
                "status": "CRITICAL",
                "current": 23.4,
                "baseline": 0.2,
                "threshold": 1.0,
                "p5m_avg": 21.8,
                "p15m_avg": 14.2,
                "p1h_avg": 1.1,
                "spike_started_at": (now - timedelta(minutes=11)).isoformat(),
            },
            "latency": {
                "name": "Request Latency p99",
                "unit": "ms",
                "status": "CRITICAL",
                "current": 4200,
                "baseline": 120,
                "threshold": 500,
                "p5m_avg": 3900,
                "p15m_avg": 2100,
                "p1h_avg": 135,
                "spike_started_at": (now - timedelta(minutes=13)).isoformat(),
            },
        }

        selected = {k: v for k, v in all_metrics.items() if k in requested}
        if not selected:
            return json.dumps({
                "error": f"No metrics matched '{metric}'",
                "valid_options": list(all_metrics.keys()),
            })

        result = {"service": service, "metrics": selected}
        return json.dumps(result, indent=2)[:2000]
    except Exception as e:
        return json.dumps({"error": str(e)})
