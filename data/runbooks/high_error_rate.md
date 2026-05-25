# Runbook: High Error Rate

## Overview
Application error rate has exceeded acceptable threshold (typically > 1% of requests) indicating degradation in service quality or partial outage.

## Trigger Conditions
- **Primary Alert:** Error rate > 1% sustained for > 2 minutes
- **Secondary Signals:**
  - Specific HTTP status codes (5xx) spike
  - Exception rate in application metrics increases
  - Customer complaints about failures in chat/support
  - Related service latency increases (cascading failures)

## Blast Radius
- **Impact:** Users encountering failures; transaction losses possible
- **Scope:**
  - Single endpoint: Users of that feature affected
  - Global: All users unable to use service
- **Customer Facing:** YES (direct user-facing failure)
- **Revenue Impact:** CRITICAL — directly impacts revenue for 100% of affected traffic
- **SLA Breach Risk:** HIGH

## Step-by-Step Remediation

### Phase 1: Assessment (0-2 min)
1. **Confirm error spike**
   ```
   # Dashboard check: error rate graph
   # Verify it's not a monitoring lag
   ```

2. **Identify affected endpoints**
   ```
   # Which endpoints have high error rate?
   # Look at error breakdown by endpoint/status code
   ```
   - Is it all endpoints or specific ones?
   - 500 errors (server-side) or 4xx (client-side)?

3. **Check service status page**
   - Any internal incidents or known issues?
   - Is a dependent service in degraded state?

4. **Review recent changes**
   ```bash
   # Was there a deployment in the last 30 minutes?
   kubectl rollout history deployment/<service>
   ```

### Phase 2: Narrow Root Cause (2-5 min)

**Scenario A: 500 Errors (Server-Side Failure)**
1. Check application logs for exceptions
   ```bash
   kubectl logs <pod> -n <namespace> --tail=100 | grep -i "error\|exception\|fatal"
   ```

2. Examine correlation:
   - Did error rate spike correlate with database latency spike?
   - Is a downstream API returning errors?
   - Are we hitting resource limits (memory, DB connections)?

3. Check dependencies
   ```bash
   # Database connectivity
   kubectl exec <pod> -- mysql -h <db_host> -u <user> -e "SELECT 1"
   
   # Cache connectivity
   kubectl exec <pod> -- redis-cli -h <cache_host> ping
   ```

**Scenario B: 4xx Errors (Bad Requests)**
1. Are clients sending malformed requests?
   ```bash
   # Check request logs for patterns
   kubectl logs <pod> -n <namespace> | grep "400\|401\|403\|404" | head -20
   ```

2. Did API contract change?
   - Was a field renamed?
   - Did validation become stricter?

**Scenario C: 503 Service Unavailable**
1. Are pods crashing or restarting?
   ```bash
   kubectl get pods -n <namespace> -l app=<service> -o wide
   ```

2. Is there resource exhaustion?
   ```bash
   kubectl top pods -n <namespace> -l app=<service>
   ```

### Phase 3: Triage & Mitigation (5-10 min)

**If Error Type = Recent Deployment**
```bash
# OPTION 1: Rollback immediately (if high error rate confirmed)
kubectl rollout undo deployment/<service> -n <namespace>

# Monitor for recovery
kubectl get events -n <namespace> | head -20
```

**If Error Type = Dependency Failure**
```bash
# Restart dependent service
kubectl rollout restart deployment/<dependency> -n <namespace>

# Or scale down broken version
kubectl scale deployment/<service> --replicas=0 -n <namespace>
```

**If Error Type = Database/Cache Issue**
```bash
# Check database health
kubectl exec <pod> -- mysql -e "SHOW PROCESSLIST\G" | head -30

# Clear connection pool (force reconnect)
kubectl set env deployment/<service> DB_POOL_RESET=true -n <namespace>
```

**If Error Type = Resource Exhaustion**
```bash
# Scale horizontally to distribute load
kubectl scale deployment/<service> --replicas=<current+2> -n <namespace>

# Monitor CPU/memory per pod
watch kubectl top pods -n <namespace> -l app=<service>
```

**If Error Type = Unknown**
1. **Reduce traffic as emergency measure**
   ```bash
   # Enable circuit breaker / rate limiting
   kubectl patch ingress <service> --type merge -p '{"spec":{"rules":[{"http":{"paths":[{"backend":{"service":{"name":"<service>","port":{"number":80}}},"pathType":"Prefix","path":"/*"}]}}]}}'
   ```

2. **Page on-call engineer immediately**
   - Error rate > 5% for > 30 sec
   - Cannot identify root cause within 2 minutes

### Phase 4: Investigation (Ongoing)

1. **Correlate with deployment/changes**
   ```bash
   # What changed in the last deployment?
   git diff <previous_tag>..<current_tag> -- src/
   ```

2. **Check error distribution**
   - Is error concentrated on specific servers?
   - Is it user-specific or request-specific?

3. **Query error logs for patterns**
   ```bash
   # Group errors by message
   kubectl logs deployment/<service> -n <namespace> --tail=500 | grep ERROR | sort | uniq -c | sort -rn
   ```

4. **Monitor key metrics**
   - Error rate trend (is it increasing or stable?)
   - Latency trend (are other requests slower?)
   - Database query latency
   - Cache hit rate

## Escalation Criteria

**Escalate to Engineering IMMEDIATELY IF:**
- Error rate > 5% sustained
- Error rate continuing to increase (trending up)
- Error occurs on user signup/checkout (revenue-impacting)
- Root cause unknown after 5 minutes
- Rollback did not resolve the issue

**Escalate to Database Team IF:**
- Error rate spikes correlate perfectly with database latency
- Database replication lag detected
- Locks or deadlocks in database
- Query timeouts or connection pool exhaustion

**Escalate to Infrastructure Team IF:**
- Node or pod resource exhaustion
- Network connectivity issues between services
- Storage/disk issues
- Container registry or image pull failures

**Page Incident Commander (Page1) IF:**
- Error rate > 10% for any duration
- Service fully unavailable (100% errors)
- Customer revenue-impacting incident
- Cannot mitigate within 10 minutes

## Follow-Up Actions
- [ ] If deployment was cause: conduct code review of deployed changes
- [ ] Increase test coverage for error paths
- [ ] Add alerting for specific error types
- [ ] Improve monitoring/dashboards for root cause identification
- [ ] Update runbook based on lessons learned
- [ ] Schedule postmortem within 24 hours
