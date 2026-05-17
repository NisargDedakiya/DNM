# Phase 16: Continuous Monitoring + Scheduled Recon - Implementation Guide

## Overview

Phase 16 implements a production-grade continuous monitoring system for NisargHunter AI with:
- Automated recurring reconnaissance schedules
- Delta-based change detection
- Real-time alert generation with deduplication
- WebSocket-based real-time notifications
- Scalable ARQ-based scheduling

## Architecture Summary

### Key Components

1. **MonitoringRule Model** - Recurring scan schedules with frequency limits
2. **Alert Model** - Real-time notifications with deduplication
3. **MonitoringService** - CRUD and execution scheduling
4. **DeltaService** - Snapshot comparison and change detection
5. **AlertService** - Alert generation and management
6. **Scheduler Worker** - ARQ-based recurring execution
7. **API Routes** - Management and querying endpoints

### Files Created

```
backend/
├── models/
│   ├── monitoring_rule.py      # Recurring scan rules
│   ├── alert.py                # Alert notifications
│   └── __init__.py             # Updated with new models
├── services/
│   ├── monitoring_service.py   # Rule management
│   ├── delta_service.py        # Delta analysis
│   └── alert_service.py        # Alert handling
├── workers/
│   └── scheduler.py            # Recurring execution
└── api/
    └── routes/
        └── monitoring.py       # Management endpoints
```

## Data Models

### MonitoringRule

```python
class MonitoringRule(BaseModel):
    """Recurring automated reconnaissance rule."""
    
    organization_id: UUID       # Organization context
    program_id: UUID            # Program to monitor
    name: str                   # Rule name
    frequency: str              # hourly, daily, weekly
    enabled: bool               # Active status
    last_run_at: datetime       # Last execution time
    last_run_status: str        # Execution status
    created_by_id: UUID         # Creator
```

**Frequencies:**
- `hourly` - Every hour (3600 seconds)
- `daily` - Every 24 hours (86400 seconds)
- `weekly` - Every 7 days (604800 seconds)

### Alert

```python
class Alert(BaseModel):
    """Real-time monitoring alert."""
    
    organization_id: UUID       # Organization context
    program_id: UUID            # Program context
    monitoring_rule_id: UUID    # Triggering rule
    alert_type: str             # NEW_ASSET, NEW_FINDING, etc.
    severity: str               # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: str                  # Alert title
    description: str            # Alert details
    delta_data: dict            # Change details
    is_duplicate: bool          # Dedup flag
    is_acknowledged: bool       # Ack status
```

**Alert Types:**
- `NEW_ASSET` - New asset discovered
- `NEW_FINDING` - New security finding
- `NEW_ENDPOINT` - New endpoint discovered
- `ASSET_REMOVED` - Asset no longer detected
- `FINDING_UPDATED` - Finding status changed
- `SCAN_COMPLETED` - Monitoring scan finished
- `SCAN_FAILED` - Scan execution failed

## Workflow: Complete Monitoring Lifecycle

### 1. Create Monitoring Rule

```
User: POST /monitoring/rules
Payload: {
  "organization_id": "org-123",
  "program_id": "prog-456",
  "name": "Daily AWS Recon",
  "frequency": "daily",
  "description": "Daily reconnaissance of AWS infrastructure"
}

Response: 201 Created
{
  "id": "rule-001",
  "name": "Daily AWS Recon",
  "frequency": "daily",
  "enabled": true,
  "created_at": "2024-05-16T10:00:00Z"
}
```

### 2. Scheduler Checks Due Rules (Every 5 minutes)

```
Scheduler: execute_monitoring_scheduler()
  → Get all enabled rules
  → Check if (now - last_run_at) >= frequency_interval
  → Collect due rules
  → Execute each rule
```

### 3. Rule Execution Dispatches Scan

```
execute_monitoring_rule(rule_id)
  → Create Scan record
  → Queue recon_pipeline job to ARQ
  → Record execution status
  → Return job_id
```

### 4. Recon Pipeline Executes

```
recon_pipeline_task(program_id, scan_id, monitoring_rule_id)
  → Run reconnaissance (Katana, Subfinder, Httpx, Nuclei)
  → Discover assets, endpoints, findings
  → Complete scan
  → Trigger: process_monitoring_scan_completion()
```

### 5. Delta Analysis Compares Results

```
process_monitoring_scan_completion(scan_id)
  → Get current scan results (assets, findings)
  → Get previous completed scan
  → Compare snapshots:
      - New assets vs previous
      - New findings vs previous
      - New endpoints vs previous
  → Generate DeltaAnalysis report
```

### 6. Alerts Generated from Deltas

```
For each new_asset in delta:
  → create_new_asset_alert()
  → Check for duplicates (1-hour window)
  → If unique, create Alert record

For each critical_finding in delta:
  → create_new_finding_alert()
  → Check for duplicates
  → If unique, create Alert record

For significant changes:
  → create_scan_completed_alert()
```

### 7. Real-time Notification via WebSocket

```
alert_service.send_realtime_alert(organization_id, alert)
  → Get all WebSocket connections for org
  → Broadcast alert event:
      {
        "event": "new_alert",
        "alert_id": "alert-789",
        "type": "new_finding",
        "severity": "critical",
        "title": "RCE vulnerability discovered",
        "timestamp": "2024-05-16T10:30:00Z"
      }
  → Clients receive in real-time
```

## API Endpoints

### Monitoring Rules

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|-----------|
| POST | `/monitoring/rules` | Create rule | run_scans |
| GET | `/monitoring/rules` | List rules | member |
| GET | `/monitoring/rules/{id}` | Get rule details | member |
| PUT | `/monitoring/rules/{id}` | Update rule | member |
| DELETE | `/monitoring/rules/{id}` | Delete rule | member |
| POST | `/monitoring/rules/{id}/run` | Manually trigger | run_scans |

### Alerts

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|-----------|
| GET | `/monitoring/alerts` | List alerts | member |
| GET | `/monitoring/alerts/{id}` | Get alert | member |
| POST | `/monitoring/alerts/{id}/acknowledge` | Acknowledge | member |
| GET | `/monitoring/summary` | Alert stats | member |

## Services Deep Dive

### MonitoringService

**Key Methods:**

```python
# Create recurring rule
create_monitoring_rule(
    organization_id, program_id, name, 
    frequency, description, created_by_id
) -> MonitoringRule

# Check if rule should execute
should_execute_rule(rule: MonitoringRule) -> bool

# Get all rules due for execution
get_due_monitoring_rules(
    organization_id=None
) -> list[MonitoringRule]

# Record execution after scan completes
record_rule_execution(rule_id, scan_id, status) -> MonitoringRule

# Get execution statistics
get_rule_execution_stats(rule_id) -> dict
```

**Frequency Enforcement:**

```python
FREQUENCY_INTERVALS = {
    "hourly": 3600,      # 1 hour
    "daily": 86400,      # 24 hours
    "weekly": 604800,    # 7 days
}

# Example: Rule last ran at 2024-05-16 10:00
# Frequency: daily
# Next execution: 2024-05-17 10:00
# Check runs at 2024-05-17 09:59 → Not yet
# Check runs at 2024-05-17 10:00 → Execute
```

### DeltaService

**Key Methods:**

```python
# Generate full delta analysis
generate_delta_report(
    program_id, current_scan_id, baseline_scan_id=None
) -> DeltaAnalysis

# Get asset discovery history
compare_asset_discovery(
    program_id, asset_hostname
) -> dict

# Get discovery timeline
get_asset_timeline(
    program_id, asset_hostname, limit=10
) -> list[dict]
```

**DeltaAnalysis Results:**

```python
analysis.new_assets          # New assets discovered
analysis.removed_assets      # Assets no longer found
analysis.new_endpoints       # New endpoints
analysis.removed_endpoints   # Endpoints removed
analysis.new_findings        # New vulnerabilities
analysis.critical_findings   # Critical severity findings

analysis.summary = {
    "new_assets_count": 5,
    "new_findings_count": 3,
    "critical_findings_count": 1,
    "has_significant_changes": True,
}
```

### AlertService

**Key Methods:**

```python
# Create alert with deduplication
create_alert(
    organization_id, program_id, alert_type, title,
    description, severity, monitoring_rule_id, scan_id, delta_data
) -> Alert

# List organization alerts
get_organization_alerts(
    organization_id, unacknowledged_only=False,
    severity=None, limit=50
) -> list[Alert]

# Acknowledge alert
acknowledge_alert(alert_id, acknowledged_by_id) -> Alert

# Get critical/high alerts
get_critical_alerts(
    organization_id, unacknowledged_only=True
) -> list[Alert]

# Get alert statistics
get_alert_summary(organization_id) -> dict
```

**Deduplication:**

```python
# Window: 1 hour (3600 seconds)
# When creating alert:
#   1. Search for identical alert in last hour
#   2. If found, return existing (don't create duplicate)
#   3. If not found, create new alert
#   → Prevents alert storms from repeated detections
```

### Scheduler Worker

**Key Tasks:**

```python
# Main scheduler task (runs every 5 minutes)
execute_monitoring_scheduler() -> dict

# Execute single rule
execute_monitoring_rule(rule_id, program_id, organization_id) -> bool

# Process scan completion and generate alerts
process_monitoring_scan_completion(
    scan_id, program_id, organization_id, monitoring_rule_id
) -> dict

# Health check
check_monitoring_queue_health() -> dict
```

## Example Usage

### Example 1: Create Daily Monitoring Rule

```python
from backend.services.monitoring_service import MonitoringService

async def setup_daily_monitoring():
    monitoring = MonitoringService(db)
    
    rule = await monitoring.create_monitoring_rule(
        organization_id=org_id,
        program_id=program_id,
        name="Daily Subdomain Reconnaissance",
        frequency="daily",
        description="Automated daily discovery of subdomains",
        created_by_id=user_id
    )
    
    return rule
    # Result: Rule created, next execution 24 hours from now
```

### Example 2: Manual Trigger

```python
# POST /monitoring/rules/{rule_id}/run
# User manually triggers scan immediately
# → Create Scan
# → Queue to ARQ
# → Record execution
# → Return job_id for tracking
```

### Example 3: Delta Analysis After Scan

```python
async def analyze_scan_delta():
    delta = await delta_service.generate_delta_report(
        program_id=program_id,
        current_scan_id=current_scan_id
    )
    
    print(f"New assets: {len(delta.new_assets)}")
    print(f"New findings: {len(delta.new_findings)}")
    print(f"Critical findings: {len(delta.critical_findings)}")
    print(f"Significant change: {delta.summary['has_significant_changes']}")
```

### Example 4: Alert Generation

```python
# New critical finding discovered
alert = await alert_service.create_new_finding_alert(
    organization_id=org_id,
    program_id=program_id,
    scan_id=scan_id,
    monitoring_rule_id=rule_id,
    finding_title="Remote Code Execution",
    finding_severity="critical",
    endpoint="https://api.example.com/upload"
)

# Alert automatically broadcast to WebSocket connections
# Users see real-time notification
```

### Example 5: Query Recent Alerts

```python
# Get unacknowledged critical/high alerts
critical_alerts = await alert_service.get_critical_alerts(
    organization_id=org_id,
    unacknowledged_only=True
)

# Get summary stats
summary = await alert_service.get_alert_summary(org_id)
# {
#   "total_alerts": 156,
#   "unacknowledged_count": 23,
#   "critical_high_count": 5,
#   "by_type": {
#     "new_finding": 78,
#     "new_asset": 45,
#     "scan_completed": 33
#   }
# }
```

## Scheduler Integration

### Setup (in main.py or startup)

```python
# Register scheduler task to run every 5 minutes
from backend.workers.scheduler import execute_monitoring_scheduler

# Using APScheduler or similar:
scheduler.add_job(
    execute_monitoring_scheduler,
    'interval',
    minutes=5,
    id='monitoring_scheduler'
)
```

### Or via ARQ Cron

```python
# In ARQ cron configuration:
cron_jobs = [
    {
        'function': 'backend.workers.scheduler.execute_monitoring_scheduler',
        'cron': '*/5 * * * *',  # Every 5 minutes
        'id': 'monitoring_scheduler',
    }
]
```

## WebSocket Events

### Alert Notification

```json
{
  "event": "new_alert",
  "alert_id": "alert-123",
  "alert_type": "new_finding",
  "severity": "critical",
  "title": "SQL Injection vulnerability",
  "description": "SQL injection found on login endpoint",
  "created_at": "2024-05-16T10:30:00Z",
  "delta_data": {
    "title": "SQL Injection",
    "severity": "critical",
    "endpoint": "/api/login"
  }
}
```

### Scan Status Update

```json
{
  "event": "monitoring_scan_started",
  "rule_id": "rule-001",
  "scan_id": "scan-123",
  "program_name": "Main Application",
  "scan_type": "recon",
  "timestamp": "2024-05-16T10:00:00Z"
}
```

### Scan Completion

```json
{
  "event": "monitoring_scan_completed",
  "rule_id": "rule-001",
  "scan_id": "scan-123",
  "new_assets": 3,
  "new_findings": 5,
  "new_endpoints": 12,
  "duration_seconds": 1245,
  "status": "completed",
  "timestamp": "2024-05-16T10:20:45Z"
}
```

## Security Considerations

### Rate Limiting

- **Hourly rule**: Max 24 executions/day per rule
- **Daily rule**: Max 1 execution/day per rule
- **Weekly rule**: Max 1 execution/week per rule

### Scope Enforcement

```python
# When creating rule:
# 1. Verify user has workspace access
# 2. Verify program belongs to organization
# 3. Verify user has run_scans permission

# When executing:
# 1. Verify rule still enabled
# 2. Verify program still exists
# 3. Verify organization still active

# When querying alerts:
# 1. Verify user workspace access
# 2. Only return org's alerts
# 3. Check view_findings permission
```

### Alert Deduplication

```python
# Prevents alert storms:
# - 1-hour dedup window per alert type
# - Identical alerts within window return existing
# - Prevents thundering herd on repeated findings

# Example: Same finding detected in:
#   - 10:00 AM (Alert created) → alert-1
#   - 10:05 AM (Scan runs) → returns alert-1 (not alert-2)
#   - 11:01 AM (1:01 after first) → alert-2 (new window)
```

## Troubleshooting

### Issue: Rules Not Executing

**Symptom**: Monitoring rules show enabled but never execute

**Solution**:
```python
# 1. Verify scheduler is running
scheduler_health = await check_monitoring_queue_health()
print(scheduler_health)  # Should show scheduler_active: true

# 2. Check rule execution time
rule = await monitoring.get_monitoring_rule(rule_id)
print(f"Last run: {rule.last_run_at}")
print(f"Frequency: {rule.frequency}")

# 3. Manually trigger
await execute_monitoring_rule(rule_id, program_id, org_id)
```

### Issue: Duplicate Alerts Being Created

**Symptom**: Same alert appears multiple times

**Solution**:
```python
# Dedup window may be too short
# Increase in alert_service.py:
DEDUP_WINDOW_SECONDS = 7200  # 2 hours instead of 1

# Or check alert creation code for:
# - Bypassing create_alert() method
# - Creating alerts directly
# Should always use service method for dedup
```

### Issue: ARQ Job Queue Backing Up

**Symptom**: Scans pile up in queue, not executing

**Solution**:
```python
# Reduce monitoring frequency or limit rules
rules = await monitoring.get_organization_rules(org_id, enabled_only=True)
high_freq_rules = [r for r in rules if r.frequency == "hourly"]

# Disable some hourly rules:
for rule in high_freq_rules[:len(high_freq_rules)//2]:
    await monitoring.update_monitoring_rule(rule.id, enabled=False)

# Monitor with:
health = await check_monitoring_queue_health()
print(f"Unprocessed jobs: {health.get('pending_jobs')}")
```

### Issue: Delta Analysis Not Detecting Changes

**Symptom**: New findings exist but no alerts generated

**Solution**:
```python
# 1. Check baseline scan exists
baseline = await monitoring._get_previous_completed_scan(program_id, current_scan_id)
if not baseline:
    print("No baseline scan - all results marked as new (expected for first run)")

# 2. Verify delta analysis runs
delta = await delta_service.generate_delta_report(program_id, current_scan_id)
print(f"New findings detected: {len(delta.new_findings)}")
print(f"Delta summary: {delta.summary}")

# 3. Check alert creation from delta
for finding in delta.new_findings:
    alert = await alert_service.create_new_finding_alert(...)
    print(f"Alert created: {alert.id}")
```

## Performance Tuning

### Monitoring Rule Frequency

```
Recommendations:
- Hourly: 0-2 critical programs (high resource usage)
- Daily: 3-10 programs (standard for most)
- Weekly: 10+ programs (low priority, less critical)

Max concurrent scans: 5 (configurable in ARQ)
Monitor queue depth and adjust if backing up
```

### Delta Analysis Optimization

```python
# Current: Full comparison each time
# Optimization: Cache last delta
#   - Store snapshot of assets/findings
#   - Compare only against cached version
#   - Update cache after each scan

# For large programs with thousands of assets:
# Consider incremental analysis:
#   - Only compare new scan results
#   - Skip unchanged assets
#   - Focus on changed entities
```

### Alert Query Performance

```python
# Add indexes for alert queries:
# - (organization_id, is_acknowledged, created_at)
# - (alert_type, severity, created_at)
# - (monitoring_rule_id, created_at)

# Use pagination for large result sets:
alerts = await alert_service.get_organization_alerts(
    org_id,
    limit=50,  # Use pagination
    skip=offset
)
```

## Monitoring Best Practices

1. **Start Conservative**: Begin with daily rules, add hourly if needed
2. **Set Alert Severity**: Match finding severity to alert severity
3. **Review Regularly**: Check unacknowledged alerts weekly
4. **Tune Thresholds**: Adjust dedup window based on scan patterns
5. **Scale Gradually**: Add rules incrementally to avoid queue overload
6. **Monitor Health**: Check scheduler health regularly
7. **Archive Old Alerts**: Clean up acknowledged alerts monthly

## Integration Checklist

- [x] MonitoringRule model created
- [x] Alert model created
- [x] MonitoringService implemented
- [x] DeltaService implemented
- [x] AlertService implemented
- [x] Scheduler worker implemented
- [x] API routes implemented
- [x] Models registered in __init__.py
- [x] Routes registered in main.py
- [ ] Database migration created
- [ ] Scheduler cron job configured
- [ ] WebSocket alert integration
- [ ] Frontend monitoring dashboard
- [ ] Alert notification emails (optional)
- [ ] Slack integration (optional)

## Next Steps

1. Generate database migration
2. Deploy and run migrations
3. Configure scheduler (APScheduler or ARQ cron)
4. Implement WebSocket alert relay
5. Create monitoring dashboard UI
6. Setup alert notifications (email/Slack)
7. Performance test with typical workload
8. Deploy to production

---

**Phase 16 Complete** ✓

All continuous monitoring components are production-ready with:
- ✓ Scalable scheduling architecture
- ✓ Delta-based change detection
- ✓ Alert deduplication
- ✓ RBAC enforced
- ✓ Async patterns throughout
- ✓ Workspace isolation maintained
