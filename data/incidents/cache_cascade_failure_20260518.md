# Incident: Cache Cascade Failure — May 18, 2026

## Summary
Redis cache became unavailable, triggering database overload. Response times increased from 150ms to 8000ms.

## Timeline
- **09:15 UTC** — Redis master node disk fills to 100%
- **09:16 UTC** — Cache write operations begin failing
- **09:17 UTC** — Database queries increase 50x as cache misses multiply
- **09:18 UTC** — Database CPU jumps to 95%, queries queue
- **09:19 UTC** — Service latency exceeds SLA (500ms threshold)
- **09:21 UTC** — Customer support receives spike of timeout complaints
- **09:23 UTC** — On-call engineer pages infrastructure team
- **09:28 UTC** — Redis disk cleared (old snapshots deleted)
- **09:30 UTC** — Cache recovered, hit rate returns to 95%
- **09:35 UTC** — All metrics normalized

## Root Cause
Redis persistence (AOF - Append Only File) was set to `fsync=always`, writing every operation to disk. Combined with a user analytics spike (3x normal load), the disk filled in 4 minutes. The cache configuration lacked automatic cleanup for old snapshots.

## Impact
- Duration: 20 minutes of degraded performance
- Peak latency: 8 seconds (vs. normal 150ms)
- Affected requests: ~500,000
- User complaints: 127

## Resolution
1. Manually deleted old AOF snapshots to free disk space
2. Changed Redis fsync policy to `fsync=everysec`
3. Restarted Redis daemon
4. Monitored cache recovery

## Postmortem Actions
- [ ] Implement Redis disk usage alerting at 80% threshold
- [ ] Configure automatic AOF rewrite on 50% growth
- [ ] Add metrics: cache hit rate, eviction rate, disk free space
- [ ] Set up Redis cluster with monitoring
