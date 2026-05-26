from typing import Dict, Any

def render_p1_alert(finding: Dict[str, Any]) -> str:
    return f"""
🚨 *P1 CRITICAL ALERT* 🚨
*Target:* `{finding.get('target', 'Unknown')}`
*Title:* {finding.get('title', 'Unknown Finding')}

*Severity:* 🔥 {finding.get('severity', 'CRITICAL')}
*AI Confidence:* {finding.get('ai_confidence', 0.0) * 100:.1f}%

*Summary:*
{finding.get('summary', 'No summary provided.')}

*Exploitability:*
{finding.get('exploitability_summary', 'Pending analysis.')}
"""

def render_approval_request(request: Dict[str, Any]) -> str:
    return f"""
⚠️ *ACTION REQUIRED: Approval Gate* ⚠️
*Target:* `{request.get('target', 'Unknown')}`
*Tool/Action:* {request.get('action', 'Unknown')}
*Risk Level:* ☢️ {request.get('risk_level', 'HIGH')}

*Details:*
{request.get('details', 'Please review the requested action.')}

Do you authorize this execution?
"""

def render_daily_digest(digest: Dict[str, Any]) -> str:
    return f"""
📊 *DAILY RECON DIGEST* 📊
*Active Hunts:* {digest.get('active_hunts', 0)}
*New Findings (24h):* {digest.get('new_findings', 0)}
*P1/P2 Summary:* {digest.get('p1_p2_count', 0)} high severity alerts.

*AI Recommendations:*
{digest.get('ai_recommendations', 'Continue monitoring.')}
"""

def render_report_notification(report: Dict[str, Any]) -> str:
    return f"""
📄 *REPORT GENERATED* 📄
*Target:* `{report.get('target', 'Unknown')}`
*Status:* ✅ Ready for download.

*Summary:*
{report.get('summary', 'Complete penetration testing report.')}
"""

def render_scan_completed(scan: Dict[str, Any]) -> str:
    return f"""
✅ *SCAN COMPLETED* ✅
*Target:* `{scan.get('target', 'Unknown')}`
*Status:* {scan.get('status', 'Completed')}
*Findings:* {scan.get('findings_count', 0)} new issues discovered.
"""
