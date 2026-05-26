from enum import Enum

class Permission(str, Enum):
    FINDINGS_READ = "findings.read"
    FINDINGS_WRITE = "findings.write"
    
    REPORTS_SUBMIT = "reports.submit"
    
    SCANS_EXECUTE = "scans.execute"
    
    APPROVALS_GRANT = "approvals.grant"
    
    GRAPH_READ = "graph.read"
    
    SCHEDULER_MANAGE = "scheduler.manage"
    
    ORG_MANAGE = "org.manage"
