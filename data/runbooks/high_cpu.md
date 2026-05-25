# Runbook: High CPU Usage

## Overview
This runbook addresses sustained CPU utilization above threshold (typically 80%+) on production services.

## Trigger Conditions
- **Primary Alert:** CPU utilization > 80% sustained for > 5 minutes
- **Secondary Signals:**
  - Load average > 2x number of CPU cores
  - Context switch rate > 50,000/sec
  - System responsiveness degraded (SSH latency > 5s)

## Blast Radius
- **Impact:** Service degradation, increased latency, potential timeouts
- **Scope:** Single pod/instance initially; can cascade if unresolved
- **Customer Facing:** YES — users see slower response times
- **Revenue Impact:** HIGH — typically correlated with checkout/API failures

## Step-by-Step Remediation

### Phase 1: Immediate Assessment (0-2 min)
1. **Confirm the alert**
   ```
   top -n 1 | head -20
   ```
   Look for processes consuming > 50% CPU individually

2. **Check deployment timeline**
   - Was a deployment made in the last 30 minutes?
   - `kubectl describe deployment <service>` to review rollout status
   - If YES → consider rollback (see Escalation Criteria)

3. **Identify hot process**
   ```
   ps aux --sort=-%cpu | head -10
   ```
   - What PID is consuming the most CPU?
   - Is it the expected service process or a rogue process?

### Phase 2: Root Cause Hypothesis (2-5 min)
1. **Check recent code changes**
   - `git log --oneline -10` on affected service
   - Any database query changes, loop optimizations, or resource exhaustion patterns?

2. **Examine metrics correlation**
   - Did CPU spike correlate with:
     - Increase in request volume? (check QPS graphs)
     - Change in request complexity? (long-running queries?)
     - Memory pressure? (OOM killer activity?)
     - Disk I/O spike? (symlink to CPU via kernel saturation)

3. **Check for resource limits**
   - Is the container/instance constrained?
   - `kubectl describe pod <pod>` → check requests/limits
   - `free -h` → is memory low, causing swap thrashing?

### Phase 3: Mitigation (5-10 min)

**Option A: Graceful Scale-Up (Preferred)**
```bash
# Horizontally scale the deployment
kubectl scale deployment <service> --replicas=<current+2>
```
- Distributes load across more pods
- Gives time to investigate without service impact

**Option B: Reduce Load (If scaling unavailable)**
```bash
# Enable request throttling if supported
kubectl set env deployment/<service> THROTTLE_QPS=<reduced_value>
```

**Option C: Restart Service (Last Resort)**
```bash
# Kill all pods in deployment (triggers new healthy instances)
kubectl rollout restart deployment/<service>
```
- Only if scale-up doesn't help within 2 minutes
- May cause brief traffic interruption

### Phase 4: Investigation (Ongoing)
1. **Profile the CPU usage**
   ```
   perf record -p <PID> -F 99 -- sleep 30
   perf report
   ```

2. **Check application logs**
   ```
   kubectl logs <pod> --tail=100 | grep -i error
   ```

3. **Monitor after mitigation**
   - Watch CPU for next 10 minutes
   - If it drops after scale-up → likely load-related
   - If it persists → likely code issue

## Escalation Criteria

**Escalate to Engineering Immediately IF:**
- CPU remains > 90% after scale-up attempt
- CPU spike correlates with recent deployment (consider rollback)
- Multiple services in same cluster all showing high CPU simultaneously
- Problem persists > 15 minutes

**Escalate to Database Team IF:**
- CPU spike correlates with sudden increase in slow queries
- `mysqld` or `postgres` is the top CPU consumer
- Database connection pool exhausted

**Escalate to Infrastructure Team IF:**
- Host-level CPU at 100% (not just container)
- Multiple unrelated containers on same host showing high CPU
- Load average > 10x number of cores

## Follow-Up Actions
- [ ] Review deployment changes from past 30 minutes
- [ ] Add CPU profiling to affected service
- [ ] Increase CPU alert threshold if false positives detected
- [ ] Document root cause and permanent fix in postmortem
