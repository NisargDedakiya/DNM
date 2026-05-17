"""
Parsers for scanner outputs: Katana and Nuclei.

Provides normalization utilities to transform raw scanner outputs
into findings suitable for insertion into the Findings engine.
"""
from __future__ import annotations

import json
import re
from typing import List, Dict, Any


def parse_katana_output(output: str) -> List[str]:
    """Extract URLs/endpoints from katana output.

    Katana prints discovered paths/URLs; we extract http(s) endpoints.
    """
    urls: List[str] = []
    # simple regex to find http(s) URLs
    for m in re.finditer(r"https?://[a-zA-Z0-9\-._~:/?#@!$&'()*+,;=%]+", output):
        u = m.group(0).rstrip(".,\n \r")
        urls.append(u)
    # fallback: lines that look like paths
    if not urls:
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("/") and len(line) > 1:
                urls.append(line)
    # dedupe
    return sorted(list(dict.fromkeys(urls)))


def parse_nuclei_output(output: str) -> List[Dict[str, Any]]:
    """Parse nuclei JSON output (may be newline-delimited JSON).

    Returns list of dicts with keys: template_id, name, severity, host, matched, path
    """
    findings: List[Dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            # skip lines that are not JSON
            continue
        # nuclei JSON schema contains certain fields
        finding = {
            "template_id": obj.get("template_id") or obj.get("template"),
            "name": obj.get("info", {}).get("name") if obj.get("info") else obj.get("template"),
            "severity": obj.get("info", {}).get("severity") if obj.get("info") else obj.get("severity"),
            "host": obj.get("host") or obj.get("ip") or obj.get("matched") and obj.get("matched")[0:50],
            "matched": obj.get("matched") or obj.get("matcher_name"),
            "path": obj.get("path") or obj.get("uri") or None,
            "raw": obj,
        }
        findings.append(finding)
    return findings


def normalize_findings(scanner: str, raw_findings: List[Any], program_id: str | None = None) -> List[Dict[str, Any]]:
    """Convert scanner-specific findings into normalized finding dicts.

    Fields: title, severity, description, endpoint, evidence
    """
    normalized: List[Dict[str, Any]] = []
    for f in raw_findings:
        if scanner == "nuclei":
            title = f.get("name") or f.get("template_id") or "nuclei finding"
            severity = (f.get("severity") or "low").lower()
            endpoint = f.get("host")
            evidence = json.dumps(f.get("raw") or f)
            description = f.get("matched") or f.get("title") or "Detected by nuclei"
        elif scanner == "katana":
            title = "discovered endpoint"
            severity = "info"
            endpoint = f
            evidence = ""
            description = f
        else:
            title = str(f)
            severity = "low"
            endpoint = None
            evidence = str(f)
            description = str(f)

        normalized.append({
            "title": title,
            "severity": severity,
            "description": description,
            "endpoint": endpoint,
            "evidence": evidence,
            "program_id": program_id,
        })
    return normalized
