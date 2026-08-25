# Observability, Alerting and Reference Performance Acceptance

This runbook implements the operational evidence path for the Final Baseline. It does not turn an unexecuted test into a PASS: the protected staging and reference-performance workflows must produce artifacts for the release being promoted.

## Application observability

The Django service emits structured JSON-style console logs and returns request identifiers. Configure `SENTRY_DSN` through the deployment secret store to enable unhandled-error reporting. `send_default_pii` is disabled; raw request bodies, provider credentials and tenant/member data must not be added as Sentry tags or breadcrumbs.

Celery Beat executes `platform_core.tasks.monitor_operational_health` every five minutes. It raises deduplicated `SecurityAlert` records for repeated background-job, webhook and delivery failures. Platform Operations can view the **security** log and acknowledge an alert; acknowledgement itself is audited.

`/api/health/` is a liveness endpoint. `/api/ready/` checks PostgreSQL, Redis/cache, writable configured storage and the malware scanner when ClamAV is required. A release is not healthy when a mandatory dependency probe fails.

## External availability and TLS monitoring

The application cannot reliably alert when the whole application/VPS is unavailable. Run `scripts/ops-monitor.py` from an external monitoring host at least every five minutes. Set:

- `PUBLIC_BASE_URL=https://<production-host>`
- `ALERT_WEBHOOK_URL=<private operations webhook>`
- `TLS_WARN_DAYS=21`

The monitor checks liveness, readiness and TLS certificate expiry. It sends operational-only metadata to the configured webhook and returns exit code 2 on an alert condition. Configure the monitoring platform to alert on repeated non-zero exit codes as well as missed executions.

Also configure infrastructure-provider alerts for CPU, memory, disk/NVMe capacity, PostgreSQL capacity/backup failure and object-storage capacity. These remain external infrastructure signals and cannot be proven by source code alone.

## Reference dataset

The performance seed is deliberately opt-in and refuses to run unless `ALLOW_REFERENCE_LOAD_SEED=true` and a strong `LOAD_TEST_PASSWORD` is provided.

```bash
python manage.py seed_reference_load --reset \
  --tenants 100 \
  --members 50000 \
  --attendance 250000 \
  --finance 100000 \
  --documents 20000
```

The finance target creates 100,000 assessments **and** 100,000 matched payments, which meets or exceeds the baseline reference profile. Synthetic benchmark tenants use a configurable prefix and must never be created in customer production data.

## 100-session load gate

`scripts/load-test.py` opens independent authenticated sessions and continuously exercises dashboard/list/report APIs. Default acceptance settings are 100 concurrent sessions, p95 <= 700 ms and error rate <= 0.5%. The measured latency includes client/network overhead, so it is a conservative proxy for API response latency.

The GitHub workflow `Reference performance acceptance` is manual and intentionally requires a protected runner labelled `lodgeflow-reference`. That runner must provide at least the reference profile of approximately 8 vCPU, 12 GB RAM and NVMe storage. The workflow seeds the full reference dataset, executes the load gate and uploads the JSON measurement plus Docker and runner evidence.

Do not change a failing performance gate to PASS by increasing the threshold. Investigate query plans, indexes, pagination, cache behavior, worker contention and resource saturation; document any approved baseline change through change control.

## Availability and DR objectives

The operational baseline is a 99.5% monthly availability target excluding agreed maintenance, with RPO <= 24 hours and RTO <= 4 hours unless the customer contract specifies stricter values. Backup success monitoring, encrypted off-host backups and destructive non-production restore drills remain mandatory release evidence.
