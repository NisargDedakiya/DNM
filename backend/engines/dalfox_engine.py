"""
Dalfox engine for reflected XSS testing on prioritized URL targets.
"""
from __future__ import annotations

import re
from typing import Any

from backend.scanners.base_scanner import BaseScanner


class _DalfoxRunner(BaseScanner):
    def validate_target(self, target: str) -> bool:
        return bool(re.match(r"^https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$", target.strip()))

    async def run(self, target: str) -> dict[str, Any]:
        if not self.validate_target(target):
            raise ValueError("Invalid Dalfox target")

        cmd = ["dalfox", "url", target.strip(), "--format", "json", "--silence"]
        stdout, stderr = await self.execute_subprocess(cmd)
        return {"target": target, "stdout": stdout, "stderr": stderr}

    def parse_output(self, output: str) -> list[str]:
        return [line for line in output.splitlines() if line.strip()]


def prioritize_xss_targets(urls: list[str]) -> list[str]:
    """Prioritize parameter-rich and auth/admin-adjacent URLs for XSS checks."""
    scored: list[tuple[int, str]] = []

    for url in urls:
        score = 0
        u = url.lower()
        if "?" in u:
            score += 40
        if any(k in u for k in ["redirect", "next=", "url=", "return="]):
            score += 25
        if any(k in u for k in ["login", "auth", "admin", "account", "profile"]):
            score += 20
        if any(k in u for k in ["search", "q=", "query="]):
            score += 15
        scored.append((score, url))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [u for _, u in scored]


async def run_dalfox_scan(
    urls: list[str],
    timeout: int = 180,
    max_targets: int = 30,
) -> dict[str, Any]:
    """Run Dalfox over prioritized URL targets with bounded execution."""
    prioritized = prioritize_xss_targets(urls)[:max_targets]
    runner = _DalfoxRunner(timeout=timeout)

    findings: list[dict[str, Any]] = []
    errors: list[str] = []

    for url in prioritized:
        try:
            result = await runner.run(url)
            lines = runner.parse_output(result["stdout"])
            for line in lines:
                findings.append({"target": url, "finding": line, "scanner": "dalfox"})
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    return {
        "scanner": "dalfox",
        "targets_scanned": len(prioritized),
        "findings": findings,
        "errors": errors,
    }
