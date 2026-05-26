"""
Jira connector helpers for issue tracking and workflow sync.
"""
from __future__ import annotations

from typing import Any


def create_ticket(project_key: str, issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_key": project_key,
        "ticket": {
            "title": str(issue.get("title") or "Security Finding"),
            "severity": str(issue.get("severity") or "medium"),
            "description": str(issue.get("description") or issue.get("summary") or ""),
        },
        "status": "created",
    }


def update_issue_status(issue_key: str, status_value: str) -> dict[str, Any]:
    return {
        "issue_key": issue_key,
        "status": status_value,
        "updated": True,
    }


def synchronize_workflow(project_key: str, workflow: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_key": project_key,
        "workflow": {
            "name": str(workflow.get("name") or "workflow"),
            "status": str(workflow.get("status") or "draft"),
            "steps": workflow.get("steps") or [],
        },
    }
