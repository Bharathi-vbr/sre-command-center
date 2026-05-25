# Incident: Database Connection Pool Exhaustion — May 20, 2026

## Summary
At 14:32 UTC, the checkout service began returning 503 errors due to all database connection pool slots being occupied.

## Timeline
- **14:28 UTC** — Payment processing latency begins increasing (observed in metrics)
- **14:32 UTC** — Error rate spike to 45% on checkout API
- **14:33 UTC** — Customer reports checkout failures in Slack
- **14:35 UTC** — On-call engineer notified via PagerDuty
- **14:38 UTC** — Root cause identified: idle connections not being released
- **14:42 UTC** — Service restarted, connection pool reset
- **14:45 UTC** — Error rate returns to < 0.1%

## Root Cause
A deployment at 14:15 UTC introduced a connection leak in the payment processing module. Each failed payment attempt left a connection open instead of properly releasing it back to the pool. With 100 connections in the pool and ~10 requests/sec failing, the pool was exhausted within 15 minutes.

## Impact
- Duration: 13 minutes
- Affected requests: ~8,000 checkout attempts
- Estimated revenue loss: $2,400 USD
- Affected users: ~2,100

## Resolution
1. Identified connection leak via database query profiling
2. Restarted checkout service to clear leaked connections
3. Immediately rolled back the problematic deployment
4. Root cause: missing `defer connection.Close()` in error handler

## Postmortem Actions
- [ ] Add connection pool metrics dashboard
- [ ] Implement connection timeout (max 5 min idle)
- [ ] Add automated connection pool alerts (> 90% utilization)
- [ ] Code review: all database error paths must close connections
