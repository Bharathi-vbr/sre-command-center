# Runbook: Pod CrashLoop

## Overview
A pod is repeatedly crashing and restarting (CrashLoopBackOff state). This indicates either a misconfiguration, dependency issue, or application startup failure.

## Trigger Conditions
- **Primary Alert:** Pod in CrashLoopBackOff for > 2 restart cycles
- **Secondary Signals:**
  - Restart count > 3 within 5 minutes
  - Pod never reaches Running state
  - Application logs show exit code non-zero

## Blast Radius
- **Impact:** Service unavailable on affected pod
- **Scope:** 
  - Single pod: Handled by Kubernetes (other replicas serve traffic)
  - All replicas: Full service outage
- **Customer Facing:** YES if all replicas affected; NO if other replicas available
- **Time to Impact:** Immediate

## Step-by-Step Remediation

### Phase 1: Gather Information (0-2 min)
1. **Verify pod state**
   ```bash
   kubectl describe pod <pod_name> -n <namespace>
   ```
   - Note the "Last State" and "Reason"
   - Check "Events" section for clues

2. **Check pod logs**
   ```bash
   # Current logs (may be empty if crashed immediately)
   kubectl logs <pod_name> -n <namespace>
   
   # Previous logs (from last restart)
   kubectl logs <pod_name> -n <namespace> --previous
   ```
   - Look for error messages, stack traces, or "command not found"

3. **Check restart count**
   ```bash
   kubectl get pod <pod_name> -n <namespace> -o jsonpath='{.status.containerStatuses[0].restartCount}'
   ```

### Phase 2: Identify Root Cause (2-5 min)

**A. Application Startup Failure (Most Common)**
```bash
# Check if application binary exists
kubectl describe pod <pod_name> -n <namespace> | grep Image

# View application startup command
kubectl get pod <pod_name> -n <namespace> -o jsonpath='{.spec.containers[0].command}'
```
- Is the command correct?
- Are required arguments missing?
- Is the binary present in the image?

**B. Dependency Not Available**
Look for errors like:
- "Connection refused" → dependency service not running
- "Database connection failed" → database unreachable or wrong credentials
- "Configuration not found" → ConfigMap or Secret missing

**C. Resource Constraints**
```bash
kubectl describe pod <pod_name> -n <namespace> | grep -A 5 "Limits"
```
- OOMKilled? (Out of Memory)
- CPU throttled before crash?

**D. Health Check Failures**
```bash
kubectl get pod <pod_name> -n <namespace> -o jsonpath='{.spec.containers[0].livenessProbe}'
kubectl get pod <pod_name> -n <namespace> -o jsonpath='{.spec.containers[0].readinessProbe}'
```
- Liveness probe killing healthy container?
- Readiness probe failing immediately after startup?

### Phase 3: Mitigation (5-10 min)

**Option A: Fix Configuration**
```bash
# Update environment variables
kubectl set env deployment/<service> KEY=value -n <namespace>

# Update image if corrupted
kubectl set image deployment/<service> <container>=<new_image> -n <namespace>

# Patch command if incorrect
kubectl patch deployment/<service> --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["correct","command"]}]' -n <namespace>
```

**Option B: Temporarily Disable Crashing**
```bash
# Scale deployment to 0 (stops pod)
kubectl scale deployment <service> --replicas=0 -n <namespace>

# Fix the issue asynchronously
# Then scale back up when ready
kubectl scale deployment <service> --replicas=3 -n <namespace>
```

**Option C: Rollback Deployment**
```bash
# If crash occurred after recent deployment
kubectl rollout undo deployment/<service> -n <namespace>

# Monitor for recovery
kubectl get pods -n <namespace> -l app=<service>
```

### Phase 4: Investigation (Ongoing)
1. **Compare with previous working version**
   - Did a new image tag get deployed?
   - Were environment variables changed?

2. **Test pod locally**
   ```bash
   # Run pod with debugging shell (override entrypoint)
   kubectl run debug-pod --image=<image> -it --entrypoint=/bin/bash -n <namespace>
   ```

3. **Check related services**
   ```bash
   # Are dependencies running?
   kubectl get pods -n <namespace> -l app=dependency
   ```

## Escalation Criteria

**Escalate to Engineering Immediately IF:**
- Application crash happens immediately (within 1 second)
- All replicas affected (full service outage)
- Problem persists after rollback
- Crash is due to data corruption or inconsistent state

**Escalate to Platform/Infrastructure Team IF:**
- Pod crashes with OOMKilled reason
- Node disk pressure or memory pressure
- Image pull errors or registry issues
- Kubelet or container runtime errors

**Page On-Call If:**
- All replicas in CrashLoop
- No previous working version to rollback to
- Customer-facing service (P1) is impacted
- Cannot determine root cause within 5 minutes

## Follow-Up Actions
- [ ] Review deployment YAML for correctness
- [ ] Add startup logging to catch early failures
- [ ] Increase startup timeout if needed
- [ ] Ensure liveness/readiness probes are not too aggressive
- [ ] Document the fix and update deployment templates
