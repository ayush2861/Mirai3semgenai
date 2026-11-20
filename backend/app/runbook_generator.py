import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

RUNBOOK_FILENAME = "titancloud_sre_incident_runbook_50p.pdf"

PAGES_DATA = [
    # Page 1
    {
        "title": "TitanCloud Global Platform: SRE Incident Runbook & Operational Architecture",
        "section": "1.0 Platform Architecture & Operational Framework",
        "content": """
<b>Document Title:</b> TitanCloud Enterprise SRE Incident Runbook (50-Page Enterprise Reference Edition)<br/>
<b>Classification:</b> Confidential — Internal Infrastructure Engineering & SRE Operations<br/>
<b>Document ID:</b> TC-SRE-RUNBOOK-2026-V4<br/>
<b>Target Services:</b> TitanCloud Core Microservices, Kubernetes Ingress, Aurora Postgres Clusters, Kafka Ingestion, Redis Tier-0 Cache, and Multi-Cloud BGP Transit.<br/><br/>

<b>1.1 Executive Summary & SLA Commitments</b><br/>
TitanCloud maintains a strict 99.99% monthly availability Service Level Objective (SLO) for all Tier-1 consumer-facing APIs and a 99.95% SLO for batch and asynchronous ingestion pipelines. Monthly service availability is monitored via automated synthetic probes from 12 global points of presence (PoP). Unplanned downtime triggers automated PagerDuty escalation to the Primary SRE On-Call and secondary domain specialists within 180 seconds.
"""
    },
    # Page 2
    {
        "title": "Service Level Agreements (SLAs) & Service Credit Eligibility Matrix",
        "section": "1.1 SLA & Financial Service Credits",
        "content": """
<b>1.2 SLA Tiers and Downtime Calculation</b><br/>
Monthly Downtime is calculated as: <code>Monthly Downtime % = (Total Outage Minutes / Total Scheduled Minutes in Calendar Month) * 100</code>.<br/>
Scheduled maintenance windows announced at least 72 hours in advance are excluded from downtime calculations.<br/><br/>
<b>Service Credit Penalty Tiers:</b><br/>
• <b>Tier A Availability (≥ 99.99%):</b> 0% Service Credit. Operations meet baseline SLA commitment.<br/>
• <b>Tier B Availability (99.90% – 99.98%):</b> 10% Service Credit applied against the client's subsequent monthly billing cycle.<br/>
• <b>Tier C Availability (99.00% – 99.89%):</b> 25% Service Credit applied to account balance.<br/>
• <b>Tier D Availability (< 99.00%):</b> 50% Service Credit plus mandatory executive post-mortem review submitted to customer within 5 business days.<br/><br/>
<b>Eligibility Criteria:</b> Customers must lodge an SLA compensation claim via the TitanCloud Enterprise Support Portal within 30 days of the documented incident closure. SRE Incident Commander sign-off is mandatory.
"""
    },
    # Page 3
    {
        "title": "Incident Severity Classification & Escalation Timelines",
        "section": "1.2 Incident Command System (ICS)",
        "content": """
<b>Severity Level Criteria:</b><br/>
• <b>SEV-1 (Critical / Catastrophic):</b> Complete outage or degradation affecting > 20% of customer traffic, data corruption risk, or complete payment processing outage. MTTD target: < 3 minutes. MTTR target: < 30 minutes.<br/>
• <b>SEV-2 (Major Impact):</b> Significant redundancy loss, elevated API error rate (> 5%), or critical background replication lag exceeding 10 minutes. MTTD: < 10 minutes. MTTR: < 2 hours.<br/>
• <b>SEV-3 (Moderate / Minor):</b> Non-customer facing internal tool failure, single node failover succeeded, or minor batch delay. MTTR: < 8 hours.<br/>
• <b>SEV-4 (Informational / Low):</b> Low-priority warning, minor cosmetic defect, or documentation clarification. Resolved within normal sprint cycles.<br/><br/>
<b>Escalation Matrix:</b><br/>
Primary On-Call responds within 5 minutes. If unacknowledged within 10 minutes, PagerDuty automatically pages the Secondary On-Call and SRE Engineering Director.
"""
    },
    # Page 4
    {
        "title": "Kubernetes Cluster Outage — Control Plane & etcd Quorum Loss",
        "section": "2.0 Kubernetes Infrastructure Incidents",
        "content": """
<b>Symptoms:</b> <code>kubectl</code> commands fail with <code>Error: connection refused</code> or <code>etcd cluster is unavailable or misconfigured</code>. Ingress pods unable to register endpoints.<br/><br/>
<b>Diagnostic Procedure:</b><br/>
1. Validate master node connectivity:<br/>
<code>ssh bastion.prod.titancloud.internal -p 2222</code><br/>
2. Inspect etcd member health across control plane nodes:<br/>
<code>ETCDCTL_API=3 etcdctl --endpoints=https://10.200.0.11:2379,https://10.200.0.12:2379,https://10.200.0.13:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/healthcheck-client.crt --key=/etc/kubernetes/pki/etcd/healthcheck-client.key endpoint health</code><br/>
3. Check etcd leader election status and database file size:<br/>
<code>ETCDCTL_API=3 etcdctl --write-out=table endpoint status</code><br/>
4. If database exceeds 8GB quota limit (alarm: <code>NOSPACE</code>), execute defragmentation and compaction:<br/>
<code>ETCDCTL_API=3 etcdctl compact $(etcdctl get "" --prefix --keys-only --limit=1 | grep -o '[0-9]*')</code><br/>
<code>ETCDCTL_API=3 etcdctl defrag --endpoints=https://10.200.0.11:2379</code>
"""
    },
    # Page 5
    {
        "title": "Kubernetes Node NotReady Cascades & Kubelet Failure",
        "section": "2.1 Worker Node Failure Modes",
        "content": """
<b>Problem Description:</b> Multiple worker nodes switch to <code>NotReady</code> state simultaneously, triggering pod eviction cascades and capacity collapse in production pools.<br/><br/>
<b>Root Causes:</b><br/>
1. Disk pressure on <code>/var/lib/docker</code> or <code>/var/lib/containerd</code>.<br/>
2. PIDs exhaustion (kernel <code>max_pids</code> hit due to goroutine leaks).<br/>
3. Calico / Cilium CNI agent crash or BGP peering disconnection with top-of-rack switches.<br/><br/>
<b>Triage Commands:</b><br/>
<code>kubectl get nodes -o wide --sort-by='.status.conditions[?(@.type==\"Ready\")].lastTransitionTime'</code><br/>
<code>kubectl describe node titan-node-prod-worker-042 | grep -A 8 Conditions</code><br/>
<code>journalctl -u containerd -u kubelet -n 200 --no-pager</code><br/><br/>
<b>Mitigation:</b> If containerd hung on snapshot cleanup, restart containerd safely without dropping running pods: <code>systemctl restart containerd</code>. Drain stuck node with <code>kubectl drain titan-node-prod-worker-042 --ignore-daemonsets --delete-emptydir-data --force</code>.
"""
    },
    # Page 6
    {
        "title": "Kubernetes Ingress Controller & CoreDNS Saturation",
        "section": "2.2 Ingress & DNS Infrastructure",
        "content": """
<b>Issue:</b> Elevated 503 Service Unavailable responses at the NGINX Ingress boundary, correlated with internal DNS resolution timeouts.<br/><br/>
<b>Verification & Telemetry:</b><br/>
• Inspect CoreDNS metrics in Prometheus: <code>coredns_dns_request_duration_seconds_bucket{quantile=\"0.99\"} > 0.05</code>.<br/>
• Check DNS query drop rate: <code>sum(rate(coredns_dns_responses_total{rcode=\"SERVFAIL\"}[2m])) by (instance)</code>.<br/><br/>
<b>Remediation Protocol:</b><br/>
1. Scale CoreDNS replica count immediately:<br/>
<code>kubectl scale deployment coredns -n kube-system --replicas=16</code><br/>
2. Verify node-local-dns cache daemonset rollout:<br/>
<code>kubectl rollout status daemonset/node-local-dns -n kube-system</code><br/>
3. Check NGINX Ingress upstream error logs:<br/>
<code>kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=500 | grep 'upstream timed out'</code>
"""
    },
    # Page 7
    {
        "title": "Kubernetes CrashLoopBackOff & Out-Of-Memory (OOMKilled) Storms",
        "section": "2.3 Workload Stabilization",
        "content": """
<b>Scenario:</b> A critical downstream payment or checkout microservice encounters consecutive OOMKilled (Exit Code 137) events following a marketing promotion spike.<br/><br/>
<b>Diagnosis:</b><br/>
• Identify terminating containers: <code>kubectl get pods -A --field-selector status.phase!=Running</code><br/>
• Confirm termination reason: <code>kubectl get pod payment-service-7bb8c98-df4x2 -n core -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}'</code><br/><br/>
<b>Emergency Recovery Steps:</b><br/>
1. Temporarily patch deployment memory limits by 50%:<br/>
<code>kubectl set resources deployment payment-service -n core --limits=memory=4Gi,cpu=2000m --requests=memory=2Gi,cpu=1000m</code><br/>
2. Disable non-critical synchronous telemetry middleware via ConfigMap flag <code>ENABLE_PROFILING=false</code>.<br/>
3. Trigger gradual rollout: <code>kubectl rollout restart deployment/payment-service -n core</code>.<br/>
4. Monitor Prometheus memory saturation gauge: <code>container_memory_working_set_bytes / kube_pod_container_resource_limits{resource=\"memory\"}</code>.
"""
    },
    # Page 8
    {
        "title": "Kubernetes Pod Eviction & Ephemeral Storage Exhaustion",
        "section": "2.4 Node Storage Management",
        "content": """
<b>Indicator:</b> Worker nodes report <code>DiskPressure = True</code>, causing the kube-scheduler to evict lowest priority pods.<br/><br/>
<b>Investigation:</b><br/>
• Inspect node filesystem usage: <code>df -h /var/log /var/lib/containerd /var/lib/kubelet</code>.<br/>
• Locate runaway container logs: <code>du -sh /var/log/pods/* | sort -hr | head -n 10</code>.<br/><br/>
<b>Resolution:</b><br/>
1. Purge unreferenced container images:<br/>
<code>crictl rmi --prune</code><br/>
2. Truncate oversized runaway log files:<br/>
<code>find /var/log/pods/ -name \"*.log\" -size +5G -exec truncate -s 100M {} \\;</code><br/>
3. Enforce <code>log-opt max-size=100m</code> and <code>max-file=5</code> in <code>/etc/docker/daemon.json</code> or containerd configuration.
"""
    },
    # Page 9
    {
        "title": "Database Replication Lag — PostgreSQL Aurora & Patroni HA",
        "section": "3.0 Relational Database SRE Runbooks",
        "content": """
<b>Severity:</b> SEV-1 if replication lag exceeds 60 seconds on read-replicas serving customer checkout requests.<br/><br/>
<b>Telemetry & Health Check:</b><br/>
Query primary PostgreSQL instance (port 5432):<br/>
<code>SELECT client_addr, application_name, state, sync_state, pg_wal_lsn_diff(pg_current_wal_lsn(), write_lsn) AS write_lag_bytes, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes, EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds FROM pg_stat_replication;</code><br/><br/>
<b>Key Thresholds:</b><br/>
• Replay lag > 500MB (524288000 bytes) triggers automated read-traffic shedding.<br/>
• Lag seconds > 120 triggers Patroni replica disqualification from automatic failover pool.<br/><br/>
<b>Corrective Actions:</b><br/>
1. Terminate long-running analytical queries blocking replay on read replica:<br/>
<code>SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state != 'idle' AND query_start < now() - INTERVAL '10 minutes' AND pid <> pg_backend_pid();</code><br/>
2. Check network bandwidth saturation between Primary AZ-1a and Replica AZ-1b.
"""
    },
    # Page 10
    {
        "title": "PostgreSQL Patroni Automated Failover & Split-Brain Mitigation",
        "section": "3.1 Database High Availability",
        "content": """
<b>Scenario:</b> Primary database node unresponsive; Patroni DCS (Consul/etcd) initiates leader election.<br/><br/>
<b>Validation Steps:</b><br/>
1. Check Patroni cluster status from bastion host:<br/>
<code>patronictl -c /etc/patroni/titan-db.yml topology</code><br/>
2. Ensure previous leader is quarantined via STONITH / AWS EC2 stop-instances to prevent split-brain writes.<br/>
3. In the event of an unprompted failover stall, force manual promotion:<br/>
<code>patronictl -c /etc/patroni/titan-db.yml failover titan-cluster --candidate titan-db-replica-02 --force</code><br/>
4. Confirm DNS / PgBouncer routing points to the new primary VIP: <code>pgbouncer-cli -p 6432 -c 'SHOW POOLS;'</code>.
"""
    },
    # Page 11
    {
        "title": "Database Connection Pool Saturation (PgBouncer Starvation)",
        "section": "3.2 Connection Pool Management",
        "content": """
<b>Symptom:</b> Application errors: <code>psycopg2.OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections</code> or <code>server_login_retry timeout</code>.<br/><br/>
<b>Diagnostic Commands:</b><br/>
Connect to PgBouncer admin console:<br/>
<code>psql -h 127.0.0.1 -p 6432 -U pgbouncer pgbouncer</code><br/>
<code>SHOW CLIENTS;</code><br/>
<code>SHOW STATS;</code><br/>
<code>SHOW CONFIG;</code><br/><br/>
<b>Resolution:</b><br/>
• If <code>cl_waiting > 50</code>, increase <code>default_pool_size</code> from 50 to 120 in <code>/etc/pgbouncer/pgbouncer.ini</code>.<br/>
• Issue live reload: <code>RELOAD;</code> (does not drop active client connections).<br/>
• Pause rogue client connections from high-volume batch jobs: <code>PAUSE core_billing_db;</code>.
"""
    },
    # Page 12
    {
        "title": "PostgreSQL Vacuum Stalls, Bloat & Transaction ID Wraparound",
        "section": "3.3 Storage Engine Maintenance",
        "content": """
<b>Risk:</b> PostgreSQL enters read-only emergency mode if autovacuum falls behind and <code>txid_current()</code> approaches 2 billion transactions.<br/><br/>
<b>Monitoring Query:</b><br/>
<code>SELECT c.oid::regclass as table_name, age(c.relfrozenxid) as xid_age, 2147483648 - age(c.relfrozenxid) as tx_until_wraparound FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema') ORDER BY age(c.relfrozenxid) DESC LIMIT 10;</code><br/><br/>
<b>Actionable Procedure:</b><br/>
If <code>tx_until_wraparound < 50,000,000</code>, immediately initiate vacuuming with elevated cost limits:<br/>
<code>SET vacuum_cost_limit = 10000;</code><br/>
<code>VACUUM FREEZE VERBOSE ANALYZE transactions_ledger;</code>
"""
    },
    # Page 13
    {
        "title": "PostgreSQL Deadlock Storms & Lock Contention Resolution",
        "section": "3.4 Lock Contention & Transaction Management",
        "content": """
<b>Alert:</b> <code>PostgresqlDeadlockDetectedCount > 20 per minute</code>.<br/><br/>
<b>Lock Investigation Query:</b><br/>
<code>SELECT blocked_locks.pid AS blocked_pid, blocked_activity.usename AS blocked_user, blocking_locks.pid AS blocking_pid, blocking_activity.usename AS blocking_user, blocked_activity.query AS blocked_statement, blocking_activity.query AS current_statement_in_blocking_process FROM pg_catalog.pg_locks blocked_locks JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation AND blocking_locks.pid != blocked_locks.pid JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid WHERE NOT blocked_locks.granted;</code><br/><br/>
<b>Remedy:</b> Terminate blocking lock holder: <code>SELECT pg_cancel_backend(blocking_pid);</code>. If unresponsive after 15s, execute hard kill: <code>SELECT pg_terminate_backend(blocking_pid);</code>.
"""
    },
    # Page 14
    {
        "title": "Database Point-In-Time Recovery (PITR) & WAL Archive Health",
        "section": "3.5 Disaster Recovery & Backup Integrity",
        "content": """
<b>Operational Requirement:</b> SRE team must verify daily that WAL archiving to S3/GCS bucket <code>s3://titancloud-db-wal-archives-prod</code> completes with zero failed segments.<br/><br/>
<b>Verification Command:</b><br/>
<code>SELECT archived_count, last_archived_wal, last_archived_time, failed_count, last_failed_wal, last_failed_time FROM pg_stat_archiver;</code><br/><br/>
<b>Recovery SLA:</b> Point-in-time recovery to any second within the past 35 days with Recovery Time Objective (RTO) ≤ 45 minutes and Recovery Point Objective (RPO) ≤ 60 seconds.<br/>
To trigger test restoration in staging sandboxes, invoke Ansible playbook: <code>ansible-playbook -i hosts pitr_drill.yml --extra-vars \"target_time='2026-11-20 04:00:00 UTC'\"</code>.
"""
    },
    # Page 15
    {
        "title": "API Gateway Failure — Envoy Proxy, Rate Limiting & 502/504 Mitigation",
        "section": "4.0 API Gateway & Traffic Ingress",
        "content": """
<b>Scenario:</b> External API Gateway encounters surge in HTTP 502 Bad Gateway and HTTP 504 Gateway Timeout errors.<br/><br/>
<b>Envoy Proxy Diagnostics:</b><br/>
• Inspect Envoy admin interface (port 15000):<br/>
<code>curl -s http://127.0.0.1:15000/stats | grep -E 'upstream_cx_connect_fail|upstream_rq_timeout|upstream_cx_overflow'</code><br/>
• Inspect circuit breaker trip counter:<br/>
<code>curl -s http://127.0.0.1:15000/stats | grep 'circuit_breakers.default.rq_open'</code><br/><br/>
<b>Mitigation Strategies:</b><br/>
1. If upstream microservices are overloaded, enable Envoy shedding at edge:<br/>
<code>curl -X POST http://127.0.0.1:15000/runtime_modify?overload.global_downstream_max_connections=15000</code><br/>
2. Bump upstream connection timeout from 2.5s to 5.0s during transit spikes.<br/>
3. Ingress Route Rule: Verify CORS pre-flight OPTIONS headers are cached for 86400s to eliminate extraneous OPTIONS query pressure on backend clusters.
"""
    },
    # Page 16
    {
        "title": "API Gateway Distributed Rate Limiting & Token Bucket Tuning",
        "section": "4.1 Rate Limiting Architecture",
        "content": """
<b>Component:</b> Redis-backed global rate limiting service (ratelimit.prod.titancloud.internal).<br/><br/>
<b>Failure Symptoms:</b> Legitimate client traffic blocked with HTTP 429 Too Many Requests, or rate limit checks failing open and flooding internal microservices.<br/><br/>
<b>Configuration & Diagnostics:</b><br/>
• Check rate limit cluster latency: <code>redis-cli -h ratelimit-redis.prod -p 6379 ping</code><br/>
• Check Redis memory usage: <code>redis-cli -h ratelimit-redis.prod info memory | grep used_memory_human</code><br/>
• Bypass rate-limiting rule for partner API key during incident: execute config change in <code>/etc/envoy/ratelimit_config.yaml</code>: set <code>unlimited: true</code> for descriptor <code>domain: titan_partner_tier1</code>.<br/>
• Reload Envoy dynamically without downtime: <code>kill -HUP $(pgrep envoy)</code>.
"""
    },
    # Page 17
    {
        "title": "API Gateway TLS Certificate Expiry & Automated ACME Renewal",
        "section": "4.2 Security & Transport Layer",
        "content": """
<b>Monitoring:</b> Prometheus alert <code>SSLCertificateExpiryHours < 72</code>.<br/><br/>
<b>Verification Command:</b><br/>
<code>echo | openssl s_client -servername api.titancloud.io -connect api.titancloud.io:443 2>/dev/null | openssl x509 -noout -dates -subject</code><br/><br/>
<b>Manual Emergency Renewal Protocol:</b><br/>
1. Trigger cert-manager Certificate request reconciliation:<br/>
<code>kubectl get certificate -n ingress-nginx</code><br/>
<code>kubectl renew certificate api-titancloud-io-tls -n ingress-nginx</code><br/>
2. In case of Let's Encrypt rate-limit lockout, switch to DigiCert Enterprise backup secret:<br/>
<code>kubectl patch ingress titan-core-ingress -n ingress-nginx --type='json' -p='[{\"op\": \"replace\", \"path\": \"/spec/tls/0/secretName\", \"value\": \"digicert-wildcard-backup-tls\"}]'</code><br/>
3. Verify TLS handshake completes cleanly: <code>curl -Iv https://api.titancloud.io/v1/health</code>.
"""
    },
    # Page 18
    {
        "title": "API Gateway Distributed Tracing & High Latency Root Cause",
        "section": "4.3 OpenTelemetry & Jaeger Inspection",
        "content": """
<b>Objective:</b> Pinpoint high 99th percentile latency (p99 > 850ms) across microservice spans.<br/><br/>
<b>Jaeger / OpenTelemetry CLI Queries:</b><br/>
• Trace lookup for slowest 1% of checkout requests:<br/>
<code>curl -s 'http://jaeger-query.observability.svc:16686/api/traces?service=checkout-api&operation=/v2/checkout/process&minDuration=800ms&limit=10' | jq '.data[].spans[] | {operationName, duration, tags}'</code><br/><br/>
<b>Remediation Decision Tree:</b><br/>
• If span latency is concentrated in <code>db.query: SELECT * FROM user_authorizations</code>: apply temporary read-through cache or index.<br/>
• If span latency is in <code>http.client: fraud-detection-service</code>: enable circuit breaker fallback to allow low-risk transactions through asynchronous queueing.<br/>
• If span latency is network DNS lookup: verify alpine container <code>ndots:5</code> issue in <code>/etc/resolv.conf</code>.
"""
    },
    # Page 19
    {
        "title": "API Gateway DDoS Defense & WAF IP Reputation Blocking",
        "section": "4.4 Edge Security & Attack Mitigation",
        "content": """
<b>Trigger:</b> HTTP request volume spikes 500% within 60s; 90% of requests originating from ASN 4134 without valid authorization tokens.<br/><br/>
<b>Cloudflare / AWS WAF Automation CLI:</b><br/>
1. Query active rate limit rules:<br/>
<code>aws wafv2 get-rate-based-statement-managed-keys-ip-set --scope CLOUDFRONT --region us-east-1 --web-acl-name TitanEdgeACL --rule-name BotSheddingRule</code><br/>
2. Emergency block malicious CIDR block:<br/>
<code>aws wafv2 update-ip-set --scope CLOUDFRONT --name BlacklistedAttackers --id 8a4c02-e91 --addresses '198.51.100.0/24' '203.0.113.0/24'</code><br/>
3. Enable Cloudflare Under Attack Mode via API token:<br/>
<code>curl -X PATCH \"https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/security_level\" -H \"Authorization: Bearer $CF_API_TOKEN\" -H \"Content-Type: application/json\" --data '{\"value\":\"under_attack\"}'</code>
"""
    },
    # Page 20
    {
        "title": "API Gateway Canary Deployments & Traffic Splitting Recovery",
        "section": "4.5 Progressive Rollouts & Rollbacks",
        "content": """
<b>Scenario:</b> Canary deployment v2.14.0 introduces subtle memory leak or 5xx regression affecting 5% canary cohort.<br/><br/>
<b>Argo Rollouts CLI Diagnosis:</b><br/>
<code>kubectl argo-rollouts get rollout core-api-service -n core</code><br/><br/>
<b>Immediate Rollback Procedure:</b><br/>
1. Abort current canary step and revert traffic 100% to stable revision:<br/>
<code>kubectl argo-rollouts abort core-api-service -n core</code><br/>
<code>kubectl argo-rollouts undo core-api-service -n core</code><br/>
2. Verify traffic split weight at Ingress:<br/>
<code>kubectl get ingress core-api-canary -n core -o jsonpath='{.metadata.annotations.nginx\\.ingress\\.kubernetes\\.io/canary-weight}'</code> (Must read <code>0</code>).<br/>
3. Confirm Prometheus HTTP 5xx error rate drops back to baseline < 0.01%.
"""
    },
    # Page 21
    {
        "title": "Critical CPU & Memory Exhaustion — Kernel cgroup Throttling & Profiling",
        "section": "5.0 Host & Container Resource Exhaustion",
        "content": """
<b>Alert:</b> <code>ContainerCPUThrottlingHigh > 40% of runtime periods</code> or <code>NodeMemoryPressure</code>.<br/><br/>
<b>Inspection Commands:</b><br/>
• Identify throttled cgroups on worker node:<br/>
<code>cat /sys/fs/cgroup/cpu/kubepods/pod*/cpu.stat | grep nr_throttled</code><br/>
• Inspect thread state on host:<br/>
<code>top -H -b -n 1 | head -n 30</code><br/>
• Capture live CPU profile using async-profiler for Java / Go services:<br/>
<code>./profiler.sh -d 30 -f /tmp/flamegraph_cpu.html $(pgrep java)</code><br/><br/>
<b>Resolution:</b><br/>
1. If application is CPU-bound on Go GC cycles, adjust environment variable: <code>GOGC=100</code> or <code>GOMEMLIMIT=3200MiB</code>.<br/>
2. If cgroup CFS quota is too tight, remove CFS quota constraint in kubelet or increase CPU limit to allow bursting.
"""
    },
    # Page 22
    {
        "title": "Memory Leaks, JVM Heap Sizing & Thread Deadlocks",
        "section": "5.1 Application Runtime Troubleshooting",
        "content": """
<b>Issue:</b> Java/JVM microservice heap utilization steadily climbs to 98% with frequent Full GC pauses > 12 seconds.<br/><br/>
<b>Telemetry & Diagnostic Commands:</b><br/>
• Capture thread dump:<br/>
<code>jcmd $(pgrep java) Thread.print > /tmp/threaddump_$(date +%s).txt</code><br/>
• Trigger compressed heap dump before pod restart:<br/>
<code>jcmd $(pgrep java) GC.heap_dump /tmp/heapdump.hprof</code><br/>
• Inspect GC activity in real time:<br/>
<code>jstat -gcutil $(pgrep java) 1000 10</code><br/><br/>
<b>Emergency Recovery:</b><br/>
Restart pods one by one: <code>kubectl rollout restart deployment/billing-engine -n core</code>.<br/>
Adjust JVM flags in Helm values: <code>-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:InitiatingHeapOccupancyPercent=45</code>.
"""
    },
    # Page 23
    {
        "title": "Disk I/O Saturation & EBS Volume IOPS Throttling",
        "section": "5.2 Storage Throughput & IOPS Limits",
        "content": """
<b>Metric:</b> <code>VolumeQueueLength > 10</code> and <code>BurstBalance = 0%</code> on AWS gp2/gp3 volumes.<br/><br/>
<b>Host I/O Diagnostic Commands:</b><br/>
<code>iostat -xz 1 5</code><br/>
Look for <code>%util > 95%</code> and high <code>await</code> times (> 25ms).<br/>
Identify processes dominating disk writes:<br/>
<code>iotop -o -b -n 2</code><br/><br/>
<b>Mitigation:</b><br/>
1. Modify EBS volume IOPS dynamically via AWS CLI:<br/>
<code>aws ec2 modify-volume --volume-id vol-0a1b2c3d4e5f6g --volume-type gp3 --iops 12000 --throughput 500</code><br/>
2. Move high-frequency ephemeral log writes to <code>tmpfs</code> RAM disk mounted at <code>/mnt/fast-tmp</code>.<br/>
3. Flush OS dirty pages: <code>sync; echo 3 > /proc/sys/vm/drop_caches</code>.
"""
    },
    # Page 24
    {
        "title": "Linux Kernel Out-Of-Memory (OOM) Killer & Dmesg Analysis",
        "section": "5.3 Linux Kernel Diagnostics",
        "content": """
<b>Symptoms:</b> Background worker daemons disappearing without container lifecycle termination hooks.<br/><br/>
<b>Verification in Kernel Ring Buffer:</b><br/>
<code>dmesg -T | grep -E -i 'oom[-_]killer|out of memory|killed process'</code><br/>
Example output: <code>Out of memory: Kill process 28419 (python3) score 852 or sacrifice child</code>.<br/><br/>
<b>Resolution & Tuning:</b><br/>
• Protect critical monitoring agents (e.g., Datadog, Node Exporter) from OOM killer:<br/>
<code>echo -1000 > /proc/$(pgrep datadog-agent)/oom_score_adj</code><br/>
• Adjust system overcommit settings in <code>/etc/sysctl.conf</code>:<br/>
<code>vm.overcommit_memory = 2</code><br/>
<code>vm.overcommit_ratio = 80</code><br/>
Apply settings: <code>sysctl -p</code>.
"""
    },
    # Page 25
    {
        "title": "Zombie Process Floods & Linux PID Table Exhaustion",
        "section": "5.4 Process Table & Subreaper Management",
        "content": """
<b>Alert:</b> <code>KernelPIDAllocationPercent > 90%</code>.<br/><br/>
<b>Inspection:</b><br/>
• Total system PIDs currently allocated: <code>cat /proc/sys/kernel/pid_max</code> (default: 32768 or 4194304).<br/>
• Find parents generating defunct/zombie child processes:<br/>
<code>ps -ef | grep defunct</code><br/>
<code>ps -eo ppid,stat | grep Z | awk '{print $1}' | sort | uniq -c | sort -nr | head -n 10</code><br/><br/>
<b>Remediation:</b><br/>
Send SIGHUP to parent to force waitpid reap: <code>kill -HUP $PARENT_PID</code>.<br/>
If parent fails to reap, terminate parent cleanly: <code>kill -TERM $PARENT_PID</code>.<br/>
Ensure all container entrypoints use <code>tini</code> or dumb-init as PID 1 to reap orphaned child processes properly.
"""
    },
    # Page 26
    {
        "title": "Kafka Consumer Lag & Partition Rebalance Stalls",
        "section": "6.0 Event Streaming & Kafka Cluster Runbooks",
        "content": """
<b>Threshold:</b> SEV-2 triggered if <code>kafka_consumergroup_lag{topic=\"transactions.events\"} > 500,000 messages</code> for > 5 consecutive minutes.<br/><br/>
<b>Diagnostic Commands:</b><br/>
Inspect consumer group lag across partitions:<br/>
<code>kafka-consumer-groups.sh --bootstrap-server kafka.prod.titancloud.internal:9092 --describe --group titan-transaction-processor</code><br/><br/>
<b>Mitigation Playbook:</b><br/>
1. If partition rebalance is stuck due to long message processing timeouts, increase <code>max.poll.interval.ms</code> to 300,000ms.<br/>
2. Scale up consumer deployment replicas to match total partition count (e.g., 32 replicas for 32 partitions):<br/>
<code>kubectl scale deployment titan-transaction-processor -n ingestion --replicas=32</code><br/>
3. If an individual partition has corrupt poison-pill message, skip offset by 1:<br/>
<code>kafka-consumer-groups.sh --bootstrap-server kafka.prod.titancloud.internal:9092 --group titan-transaction-processor --reset-offsets --to-offset 1459201 --topic transactions.events:4 --execute</code>
"""
    },
    # Page 27
    {
        "title": "Kafka Broker Disk Saturation & Under-Replicated Partitions",
        "section": "6.1 Broker Storage & High Availability",
        "content": """
<b>Alert:</b> <code>UnderReplicatedPartitions > 0</code> or <code>BrokerDiskUsagePercent > 85%</code> on broker <code>kafka-prod-04</code>.<br/><br/>
<b>Broker Diagnostics:</b><br/>
• Check under-replicated partitions across topics:<br/>
<code>kafka-topics.sh --bootstrap-server kafka.prod.titancloud.internal:9092 --describe --under-replicated-partitions</code><br/>
• Identify topics consuming largest log segment storage:<br/>
<code>du -sh /var/lib/kafka/data/* | sort -hr | head -n 15</code><br/><br/>
<b>Storage Cleanup Protocol:</b><br/>
1. Reduce retention hours temporarily on debug topics:<br/>
<code>kafka-configs.sh --bootstrap-server kafka.prod.titancloud.internal:9092 --alter --entity-type topics --entity-name audit.raw --add-config retention.ms=14400000</code> (4 hours).<br/>
2. Trigger automated segment deletion: Kafka log cleaner automatically deletes segments outside retention window.
"""
    },
    # Page 28
    {
        "title": "Kafka KRaft / Zookeeper Metadata Disconnect & Leaderless Partitions",
        "section": "6.2 Metadata Consensus Management",
        "content": """
<b>Scenario:</b> Kafka cluster loses quorum or reports <code>LeaderlessPartitions > 0</code>, halting all message production.<br/><br/>
<b>Validation & Recovery:</b><br/>
1. Check KRaft controller quorum status:<br/>
<code>kafka-metadata-shell.sh --snapshot /var/lib/kafka/metadata/__cluster_metadata-0/00000000000000000000.log</code><br/>
2. Elect preferred replicas to restore balanced leader distribution:<br/>
<code>kafka-preferred-replica-election.sh --bootstrap-server kafka.prod.titancloud.internal:9092</code><br/>
3. If partition leader remains offline, force unclean leader election (CAUTION: possible data loss):<br/>
<code>kafka-configs.sh --bootstrap-server kafka.prod.titancloud.internal:9092 --alter --entity-type topics --entity-name telemetry.logs --add-config unclean.leader.election.enable=true</code>
"""
    },
    # Page 29
    {
        "title": "Kafka Producer Backpressure & BufferExhaustedException",
        "section": "6.3 Ingestion Tier Resiliency",
        "content": """
<b>Error:</b> Microservices report <code>org.apache.kafka.common.errors.TimeoutException: Expiring 32 record(s) for topic-1:120000 ms has passed since batch creation</code>.<br/><br/>
<b>Analysis:</b><br/>
• Check broker network throughput and socket buffer queue.<br/>
• Check producer configuration: verify <code>compression.type=lz4</code> is enabled to reduce payload size by 65%.<br/>
• Verify <code>acks=1</code> for non-critical logging, or ensure sufficient broker acknowledgement buffer.<br/>
• Enable local disk spooling fallback in ingestion agents if Kafka cluster is unreachable.
"""
    },
    # Page 30
    {
        "title": "Kafka Schema Registry Outage & Avro Serialization Failures",
        "section": "6.4 Schema Registry High Availability",
        "content": """
<b>Symptom:</b> Producers receive <code>io.confluent.kafka.schemaregistry.client.rest.exceptions.RestClientException: Schema not found; error code: 40401</code>.<br/><br/>
<b>Triage:</b><br/>
• Verify Schema Registry master node:<br/>
<code>curl -s http://schema-registry.prod.titancloud.internal:8081/subjects</code><br/>
• Check compatibility mode:<br/>
<code>curl -s -X GET http://schema-registry.prod.titancloud.internal:8081/config</code> (Must be <code>BACKWARD</code> or <code>FULL</code>).<br/>
• If Schema Registry primary is hung, restart pod in namespace <code>ingestion</code>: <code>kubectl rollout restart deployment/schema-registry -n ingestion</code>.
"""
    },
    # Page 31
    {
        "title": "Redis Cache Eviction & Memory Fragmentation Emergencies",
        "section": "7.0 In-Memory Caching & Redis SRE Runbooks",
        "content": """
<b>Symptom:</b> Read latency spikes on Core Database as Redis evicts frequently used session keys.<br/><br/>
<b>Redis Diagnostic CLI:</b><br/>
<code>redis-cli -h redis-cluster.prod.titancloud.internal -p 6379 info stats</code><br/>
<code>redis-cli -h redis-cluster.prod.titancloud.internal -p 6379 info memory</code><br/><br/>
<b>Key Metrics:</b><br/>
• <code>evicted_keys > 10,000/sec</code> indicates memory exhaustion.<br/>
• <code>mem_fragmentation_ratio > 1.8</code> indicates severe OS memory fragmentation.<br/><br/>
<b>Action Plan:</b><br/>
1. Enable active memory defragmentation in real time:<br/>
<code>redis-cli -h redis-cluster.prod config set activedefrag yes</code><br/>
2. Increase maxmemory limit if host headroom permits:<br/>
<code>redis-cli -h redis-cluster.prod config set maxmemory 48gb</code><br/>
3. Purge volatile expired sessions: <code>redis-cli -h redis-cluster.prod scan 0 match 'session:anon:*' count 1000</code>.
"""
    },
    # Page 32
    {
        "title": "Redis Cluster Node Partition & Sentinel Split-Brain",
        "section": "7.1 Cache High Availability",
        "content": """
<b>Scenario:</b> Redis Sentinel fails to achieve quorum during network partition between Availability Zones.<br/><br/>
<b>Inspection:</b><br/>
<code>redis-cli -p 26379 sentinel masters</code><br/>
<code>redis-cli -p 26379 sentinel ckquorum mymaster</code><br/><br/>
<b>Mitigation:</b><br/>
1. If Sentinel reports insufficient quorum due to 1 offline sentinel node in AZ-1c, adjust quorum threshold temporarily:<br/>
<code>redis-cli -p 26379 sentinel set mymaster quorum 2</code><br/>
2. Manually trigger failover to healthy replica:<br/>
<code>redis-cli -p 26379 sentinel failover mymaster</code><br/>
3. Validate client applications reconnect to new master IP without dropping connections.
"""
    },
    # Page 33
    {
        "title": "Redis Slowlog & Hot Key Identification",
        "section": "7.2 Cache Performance Profiling",
        "content": """
<b>Alert:</b> Redis single-threaded event loop blocked, causing connection timeouts across API pods.<br/><br/>
<b>Slowlog Query:</b><br/>
<code>redis-cli -h redis-cluster.prod slowlog get 20</code><br/>
Identify commands exceeding 10,000 microseconds (e.g., <code>KEYS *</code> or unbounded <code>HGETALL</code>).<br/><br/>
<b>Hot Key Sampling:</b><br/>
Run live key analysis using Redis CLI (requires low production sampling rate):<br/>
<code>redis-cli -h redis-cluster.prod --hotkeys</code><br/>
<b>Remediation:</b> If hot key detected (e.g., global banner config accessed 50,000 times/sec), instruct client teams to implement local in-process cache (Guava/Caffeine) with 60-second TTL.
"""
    },
    # Page 34
    {
        "title": "Redis AOF & RDB Snapshot Corruption Recovery",
        "section": "7.3 Cache Persistence Integrity",
        "content": """
<b>Problem:</b> Redis server fails to restart with error: <code>Bad file format reading the append only file: make a backup of your AOF file, then use ./redis-check-aof --fix <filename></code>.<br/><br/>
<b>Recovery Steps:</b><br/>
1. Make immediate immutable backup copy of corrupted AOF file:<br/>
<code>cp /var/lib/redis/appendonly.aof /var/lib/redis/appendonly.aof.bak.$(date +%s)</code><br/>
2. Run automated AOF repair utility:<br/>
<code>redis-check-aof --fix /var/lib/redis/appendonly.aof</code><br/>
3. Start Redis service: <code>systemctl start redis-server</code>.<br/>
4. Verify key count matches expected dataset: <code>redis-cli dbsize</code>.
"""
    },
    # Page 35
    {
        "title": "Redis Cross-Region Replication & Global Active-Active Cache",
        "section": "7.4 Multi-Region Data Sync",
        "content": """
<b>Configuration:</b> Multi-region synchronization between us-east-1 (Primary) and eu-west-1 (Secondary).<br/><br/>
<b>Replication Health Check:</b><br/>
<code>redis-cli -h redis-eu.prod.titancloud.internal info replication</code><br/>
Check <code>master_link_status: up</code> and <code>master_last_io_seconds_ago < 5</code>.<br/>
If link status is <code>down</code>, inspect WAN IPsec VPN tunnel between regions.<br/>
Re-establish replication link:<br/>
<code>redis-cli -h redis-eu.prod.titancloud.internal replicaof redis-us.prod.titancloud.internal 6379</code>.
"""
    },
    # Page 36
    {
        "title": "Network Latency Investigation — BGP Routing Anomaly & Transit Flaps",
        "section": "8.0 Cloud Networking & BGP Routing",
        "content": """
<b>Alert:</b> External packet loss > 3% on US-East direct connect circuit; international p99 latency climbs to 320ms.<br/><br/>
<b>Network Diagnostics:</b><br/>
• Run MTR trace with TCP SYN packets to destination:<br/>
<code>mtr --report --report-cycles 50 --tcp --port 443 api.titancloud.io</code><br/>
• Query BGP route table state on virtual gateway:<br/>
<code>vtysh -c 'show ip bgp summary'</code><br/>
• Inspect route flap damping statistics:<br/>
<code>vtysh -c 'show ip bgp flap-statistics'</code><br/><br/>
<b>Remediation Protocol:</b><br/>
1. Shift outbound transit traffic from degraded Carrier Alpha to Carrier Bravo using BGP AS-path prepending:<br/>
<code>vtysh -c 'configure terminal' -c 'route-map PREPEND_CARRIER_ALPHA permit 10' -c 'set as-path prepend 65001 65001 65001'</code><br/>
2. Confirm router convergence within 90 seconds.
"""
    },
    # Page 37
    {
        "title": "Cross-AZ VPC Peering Degraded & MTU / Jumbo Frame Blackholes",
        "section": "8.1 AWS / Multi-Cloud VPC Peering",
        "content": """
<b>Symptom:</b> Small HTTP GET requests succeed, but large POST requests with payloads > 1500 bytes hang and timeout.<br/><br/>
<b>Diagnostic:</b> Packet MTU path discovery failure (ICMP Type 3 Code 4 Destination Unreachable blocked by Security Group).<br/><br/>
<b>Verification Command:</b><br/>
<code>ping -M do -s 1472 10.200.4.15</code> (Tests 1500 byte standard MTU).<br/>
<code>ping -M do -s 8972 10.200.4.15</code> (Tests 9000 byte Jumbo Frame).<br/><br/>
<b>Resolution:</b><br/>
• Allow ICMP Type 3 fragmentation needed in AWS Security Group rules.<br/>
• Enforce TCP MSS Clamping on border gateways: <code>iptables -t mangle -A POSTROUTING -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu</code>.
"""
    },
    # Page 38
    {
        "title": "DNS Hijack & External Authoritative DNS Server Outages",
        "section": "8.2 Global Anycast DNS Resilience",
        "content": """
<b>Monitoring:</b> Synthetic monitoring probe indicates authoritative nameservers for <code>titancloud.io</code> returning <code>REFUSED</code> in Asia-Pacific region.<br/><br/>
<b>Diagnostic Commands:</b><br/>
<code>dig +trace api.titancloud.io @8.8.8.8</code><br/>
<code>dig NS titancloud.io +nsid +nocmd +noall +answer</code><br/><br/>
<b>Failover Execution:</b><br/>
Switch secondary Anycast DNS provider from NS-Primary (Route53) to NS-Secondary (Cloudflare):<br/>
Login to registrar API and update delegations:<br/>
<code>curl -X POST https://api.registrar.com/v1/domains/titancloud.io/nameservers -d '{\"nameservers\":[\"ns1.cloudflare.com\",\"ns2.cloudflare.com\"]}'</code><br/>
Verify global propagation across public resolvers.
"""
    },
    # Page 39
    {
        "title": "Load Balancer Health Check Cascades & Thundering Herds",
        "section": "8.3 Edge Load Balancing",
        "content": """
<b>Scenario:</b> Application load balancer declares 80% of healthy target instances unhealthy simultaneously due to strict 2-second timeout.<br/><br/>
<b>Root Cause:</b> Deep health check endpoint <code>/healthz</code> executing synchronous database queries during peak traffic load.<br/><br/>
<b>Fix:</b><br/>
1. Decouple health check from database dependency: configure ALB target group to probe shallow endpoint <code>/ping</code> returning static 200 OK.<br/>
2. Adjust Target Group threshold:<br/>
<code>aws elbv2 modify-target-group --target-group-arn arn:aws:elasticloadbalancing:... --health-check-interval-seconds 15 --healthy-threshold-count 2 --unhealthy-threshold-count 5</code><br/>
3. Implement connection rate ramping to eliminate thundering herd when targets rejoin pool.
"""
    },
    # Page 40
    {
        "title": "VPN & Zero Trust Access Gateway Disconnections",
        "section": "8.4 Internal Engineering Access",
        "content": """
<b>Issue:</b> On-call engineers unable to access internal production VPC bastion hosts during active incident.<br/><br/>
<b>Triage Protocol:</b><br/>
• Verify Zero Trust tunnel daemon state:<br/>
<code>cloudflared tunnel info titan-ops-tunnel</code><br/>
• Inspect Okta SAML IdP authentication token lifetime.<br/>
• Emergency Break-Glass Access: Use hardware YubiKey token to access dedicated out-of-band console access via AWS Systems Manager Session Manager:<br/>
<code>aws ssm start-session --target i-0f9e8d7c6b5a41234 --region us-east-1</code>.
"""
    },
    # Page 41
    {
        "title": "Incident Escalation Procedures — On-Call Handoff & P1 Protocols",
        "section": "9.0 Incident Management & Escalation Framework",
        "content": """
<b>Role Definitions:</b><br/>
• <b>Incident Commander (IC):</b> Owns incident lifecycle, communication cadence, and directs mitigation. Does not write code or run commands directly.<br/>
• <b>Operations Lead (Tech Lead):</b> Executes runbook CLI commands, analyzes telemetry, coordinates engineers.<br/>
• <b>Communications Lead:</b> Updates status page (status.titancloud.io) every 15 minutes during SEV-1 incidents.<br/><br/>
<b>Escalation Timeline:</b><br/>
• <b>T+0m:</b> Alert fires on Prometheus / Datadog.<br/>
• <b>T+3m:</b> Primary on-call acknowledges PagerDuty alert.<br/>
• <b>T+5m:</b> If service impact confirmed, initiate Slack war room <code>#incident-YYYYMMDD-sev1</code>.<br/>
• <b>T+10m:</b> Incident Commander declared; executive notification sent.<br/>
• <b>T+15m:</b> Initial public customer status post: <i>\"We are investigating reports of elevated API latency...\"</i>.
"""
    },
    # Page 42
    {
        "title": "Public Status Page Management & Customer Communications",
        "section": "9.1 External Communications",
        "content": """
<b>Status Page Guidelines (status.titancloud.io):</b><br/>
• <b>Cadence:</b> Updates must be published at least every 15 minutes for SEV-1 incidents, even if no new operational progress is made.<br/>
• <b>Tone:</b> Objective, transparent, factual. Avoid speculation on root causes before telemetry confirmation.<br/><br/>
<b>Standard Status Templates:</b><br/>
• <i>Investigating:</i> \"We are currently investigating an issue impacting Core API endpoints in the US-East region. Our engineering team is actively triaging.\"<br/>
• <i>Identified:</i> \"We have identified an issue with database replication lag causing intermittent 504 timeouts. Mitigation actions are underway.\"<br/>
• <i>Monitoring:</i> \"A fix has been deployed and system metrics have stabilized. We are monitoring performance closely.\"<br/>
• <i>Resolved:</i> \"The incident is resolved. Full incident post-mortem will be published within 72 hours.\"
"""
    },
    # Page 43
    {
        "title": "On-Call Rotation Handoff & Shift Checklist",
        "section": "9.2 SRE On-Call Operations",
        "content": """
<b>Weekly Handoff Protocol (Tuesdays at 14:00 UTC):</b><br/>
The outgoing on-call engineer and incoming on-call engineer must complete the 6-point transition checklist:<br/>
1. Review all open incidents from the prior 7 days and check status of remediation tickets.<br/>
2. Verify primary and secondary phone numbers in PagerDuty and test SMS push notification.<br/>
3. Check status of all silences in Alertmanager: <code>amtool silence query</code>.<br/>
4. Verify local CLI tools: <code>kubectl</code> credentials, AWS SSO session token, and SSH bastion keys.<br/>
5. Review outstanding deployments scheduled in the current sprint.<br/>
6. Formal handoff acknowledgment recorded in <code>#sre-oncall-handoff</code>.
"""
    },
    # Page 44
    {
        "title": "Disaster Recovery (DR) Multi-Region Failover Playbook",
        "section": "9.3 Multi-Region Disaster Recovery",
        "content": """
<b>Objective:</b> Complete evacuation of Primary Region (us-east-1) to Secondary Region (us-west-2) within 15 minutes.<br/><br/>
<b>Execution Commands:</b><br/>
1. Promote Aurora Global Database replica in us-west-2:<br/>
<code>aws rds failover-global-cluster --global-cluster-identifier titan-global-db --target-db-cluster-identifier arn:aws:rds:us-west-2:123456789:cluster:titan-db-west</code><br/>
2. Shift Route53 DNS traffic weight via ARC (Application Recovery Controller):<br/>
<code>aws route53-recovery-control-config update-routing-control-states --routing-control-states-entries \"[{\"RoutingControlArn\":\"arn:aws:.../east\",\"RoutingControlState\":\"Off\"},{\"RoutingControlArn\":\"arn:aws:.../west\",\"RoutingControlState\":\"On\"}]\"</code><br/>
3. Scale up Kubernetes worker node capacity in target region using Cluster Autoscaler override.
"""
    },
    # Page 45
    {
        "title": "Security Incident Response — Compromised Credentials & Key Revocation",
        "section": "9.4 Security Incident Management",
        "content": """
<b>Trigger:</b> Suspected leak of AWS IAM secret key or Kubernetes ServiceAccount token.<br/><br/>
<b>Containment Protocol:</b><br/>
1. Immediately deactivate compromised IAM access key:<br/>
<code>aws iam update-access-key --access-key-id AKIAIOSFODNN7EXAMPLE --status Inactive --user-name svc-payment-processor</code><br/>
2. Revoke active STS assume-role sessions:<br/>
<code>aws iam put-user-policy --user-name svc-payment-processor --policy-name RevokeOldSessions --policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Deny\",\"Action\":\"*\",\"Resource\":\"*\",\"Condition\":{\"DateLessThan\":{\"aws:TokenIssueTime\":\"2026-11-20T10:00:00Z\"}}}]}'</code><br/>
3. Rotate Kubernetes Secrets: <code>kubectl delete secret payment-db-credentials -n core && helm upgrade ...</code>.
"""
    },
    # Page 46
    {
        "title": "Blameless Post-Mortem Methodology & RCA Framework",
        "section": "10.0 Post-Mortem & Continuous Reliability",
        "content": """
<b>Guiding Principle:</b> Human error is a symptom, not the root cause. Systems must be resilient to unintended actions.<br/><br/>
<b>Post-Mortem Timeline:</b><br/>
• Within 24h: Draft timeline prepared by Operations Lead.<br/>
• Within 72h: Blameless post-mortem review meeting convened with stakeholders.<br/>
• Within 5 business days: Final approved document published to internal engineering knowledge base.<br/><br/>
<b>Required Sections:</b><br/>
1. Executive Summary & Impact Metrics (Customers impacted, revenue loss, MTTR).<br/>
2. Detailed Timeline (UTC timestamps for every detection, action, and stabilization).<br/>
3. Contributing Factors & 5 Whys Analysis.<br/>
4. What Went Well vs. Where We Got Lucky vs. Action Items (Preventative JIRA tickets).
"""
    },
    # Page 47
    {
        "title": "Five Whys Root Cause Analysis (RCA) Deep Dive Template",
        "section": "10.1 Root Cause Analysis Framework",
        "content": """
<b>Example Case Study: Database Outage</b><br/>
• <b>Problem:</b> Core API returned HTTP 500 for 22 minutes.<br/>
1. <i>Why?</i> The database stopped accepting new client connections.<br/>
2. <i>Why?</i> PgBouncer ran out of free server connections.<br/>
3. <i>Why?</i> Active database queries surged from 40 to 600 simultaneous sessions.<br/>
4. <i>Why?</i> A new unindexed query on <code>invoices.created_at</code> initiated full table scans.<br/>
5. <i>Why?</i> The query was merged without passing the automated DB query performance linter in CI.<br/><br/>
<b>Action Items:</b><br/>
• Integrate automated <code>pg_qualstats</code> query cost validation into GitHub Actions CI pipeline.<br/>
• Enforce <code>statement_timeout = '3000ms'</code> globally on all client connection pools.
"""
    },
    # Page 48
    {
        "title": "SLA Service Credit Compensation Calculations & Billing Audits",
        "section": "10.2 SLA Compliance & Financial Credits",
        "content": """
<b>Formula:</b> <code>Credit Amount ($) = (Monthly Contract Value) * (Credit Percentage Tier)</code>.<br/><br/>
<b>Sample Calculation:</b><br/>
• Customer: Enterprise Partner AcmeCorp (Monthly MRR: $50,000).<br/>
• Total calendar minutes in month: 43,200.<br/>
• Documented unscheduled downtime: 65 minutes.<br/>
• Monthly Availability = <code>((43,200 - 65) / 43,200) * 100 = 99.849%</code>.<br/>
• SLA Bracket: Tier C (99.00% – 99.89%), which grants a <b>25% Service Credit</b>.<br/>
• Compensation Credit = <code>$50,000 * 0.25 = $12,500</code> applied to invoice.<br/><br/>
<b>Audit Trail:</b> Billing team verifies credit against SRE Post-Mortem Incident ID before issuing credit memo.
"""
    },
    # Page 49
    {
        "title": "Reliability Metrics: MTBF, MTTR, MTTD & Error Budgets",
        "section": "10.3 SRE Mathematical Foundations",
        "content": """
<b>Metric Definitions:</b><br/>
• <b>MTTD (Mean Time to Detect):</b> Elapsed duration between defect injection and first automated alert firing.<br/>
• <b>MTTR (Mean Time to Recover):</b> Elapsed duration between alert acknowledgment and verification of service restoration.<br/>
• <b>MTBF (Mean Time Between Failures):</b> Operational uptime hours divided by total incident count.<br/><br/>
<b>Error Budget Policy:</b><br/>
With a 99.99% monthly SLO, the allowable downtime error budget is exactly <b>4.32 minutes per month</b>.<br/>
If a team exhausts > 100% of their 30-day rolling error budget, feature releases are automatically frozen, and 100% of sprint capacity is diverted to reliability, automated testing, and technical debt remediation.
"""
    },
    # Page 50
    {
        "title": "SRE Incident Runbook Maintenance & Chaos Engineering Drills",
        "section": "10.4 Runbook Governance & Verification",
        "content": """
<b>Runbook Review Governance:</b><br/>
Every runbook page in this document must undergo semi-annual review or immediate update following any SEV-1/SEV-2 incident.<br/><br/>
<b>Chaos Engineering Drills (GameDays):</b><br/>
• SRE team conducts monthly unannounced Chaos Mesh / Litmus drills in staging and staging-like production canaries.<br/>
• Standard drill scenarios include: random node kill (<code>pod-kill</code>), synthetic network latency injection (<code>latency: 200ms ± 50ms</code>), and simulated Patroni primary database kill.<br/>
• All drill outcomes must validate that automated failover triggers within SLA targets.<br/><br/>
<b>Document Sign-off:</b><br/>
VP of Infrastructure & SRE Engineering — Approved.<br/>
Chief Information Security Officer (CISO) — Approved.<br/>
Published by TitanOps Autonomous SRE Core Engine.
"""
    }
]

def generate_50p_runbook(output_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=10
    )

    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=12
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=8
    )

    page_num_style = ParagraphStyle(
        'PageNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748B'),
        alignment=2 # Right
    )

    story = []

    for i, page_info in enumerate(PAGES_DATA):
        page_num = i + 1

        # Page Header
        header_table = Table(
            [[
                Paragraph("<b>TitanCloud Global Infrastructure — SRE Operational Runbook</b>", styles['Normal']),
                Paragraph(f"Page {page_num} of {len(PAGES_DATA)}", page_num_style)
            ]],
            colWidths=[380, 150]
        )
        header_table.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 14))

        # Title & Section
        story.append(Paragraph(page_info["section"], section_style))
        story.append(Paragraph(page_info["title"], title_style))
        story.append(Spacer(1, 8))

        # Main Content
        story.append(Paragraph(page_info["content"], body_style))

        # Footer divider if not last page
        if i < len(PAGES_DATA) - 1:
            story.append(PageBreak())

    doc.build(story)
    print(f"Successfully generated 50-page runbook PDF at: {output_path}")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "documents", RUNBOOK_FILENAME)
    generate_50p_runbook(out)
