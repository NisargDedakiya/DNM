"""
FFUF engine for high-value endpoint fuzzing with smart target prioritization.
"""
from __future__ import annotations

import re
from typing import Any

from backend.scanners.base_scanner import BaseScanner


DEFAULT_WORDLIST = "/usr/share/seclists/Discovery/Web-Content/common.txt"


class _FfufRunner(BaseScanner):
    def validate_target(self, target: str) -> bool:
        return bool(re.match(r"^https?://[a-zA-Z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$", target.strip()))

    async def run(self, target: str) -> dict[str, Any]:
        raise NotImplementedError("Use run_ffuf_scan")

    def parse_output(self, output: str) -> list[str]:
        return [line for line in output.splitlines() if line.strip()]


def prioritize_fuzz_targets(urls: list[str]) -> list[str]:
    """Prioritize admin/API/auth/upload paths for constrained fuzzing."""
    scored: list[tuple[int, str]] = []

    for url in urls:
        score = 0
        u = url.lower()
        if any(k in u for k in ["/admin", "/dashboard", "/manage"]):
            score += 40
        if any(k in u for k in ["/api", "graphql", "/v1", "/v2"]):
            score += 30
        if any(k in u for k in ["/auth", "/login", "/oauth", "/token"]):
            score += 25
        if any(k in u for k in ["upload", "file", "import"]):
            score += 20
        scored.append((score, url))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [u for _, u in scored]


async def run_ffuf_scan(
    urls: list[str],
    wordlist: str = DEFAULT_WORDLIST,
    timeout: int = 180,
    max_targets: int = 20,
) -> dict[str, Any]:
    """Run constrained FFUF on prioritized targets with low-risk defaults."""
    prioritized = prioritize_fuzz_targets(urls)[:max_targets]
    runner = _FfufRunner(timeout=timeout)

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for url in prioritized:
        if not runner.validate_target(url):
            continue

        # Safe defaults: limited threads and response filter to reduce noise/impact.
        cmd = [
            "ffuf",
            "-u",
            f"{url.rstrip('/')}/FUZZ",
            "-w",
            wordlist,
            "-t",
            "10",
            "-mc",
            "200,204,301,302,307,401,403",
            "-s",
        ]

        try:
            stdout, stderr = await runner.execute_subprocess(cmd)
            parsed = runner.parse_output(stdout)
            results.append({"target": url, "matches": parsed, "stderr": stderr})
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    return {
        "scanner": "ffuf",
        "targets_scanned": len(prioritized),
        "results": results,
        "errors": errors,
    }
