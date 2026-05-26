"""
Structured prompt templates for AI triage and report generation.
"""
from __future__ import annotations

from typing import Final


TRIAGE_TEMPLATE: Final = (
    "You are a security engineer assistant.\n"
    "Given the finding details below, return a JSON object with keys:\n"
    "- recommended_severity: one of [info, low, medium, high, critical]\n"
    "- explanation: short technical explanation of why the severity was chosen\n"
    "- remediation: concise remediation steps\n"
    "- confidence: numeric 0.0-1.0 confidence score\n"
    "Respond ONLY with valid JSON (no additional text).\n"
    "FINDING:\n"
    "Title: {title}\n"
    "Severity: {severity}\n"
    "Endpoint: {endpoint}\n"
    "Description: {description}\n"
    "Evidence: {evidence}\n"
)


REPORT_TEMPLATE: Final = (
    "You are an expert bug bounty report writer.\n"
    "Produce a markdown formatted report suitable for triage and submission.\n"
    "Include sections: Summary, Impact, Reproduction, Technical Details, Remediation, Severity Recommendation.\n"
    "The output MUST be valid Markdown only.\n"
    "FINDING:\n"
    "Title: {title}\n"
    "Severity: {severity}\n"
    "Endpoint: {endpoint}\n"
    "Description: {description}\n"
    "Evidence: {evidence}\n"
)


def render_triage_prompt(**kwargs: str) -> str:
    return TRIAGE_TEMPLATE.format(**{k: (v or "") for k, v in kwargs.items()})


def render_report_prompt(**kwargs: str) -> str:
    return REPORT_TEMPLATE.format(**{k: (v or "") for k, v in kwargs.items()})
