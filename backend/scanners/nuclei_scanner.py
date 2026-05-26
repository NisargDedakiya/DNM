"""
Nuclei scanner integration with JSON output parsing.
"""
from __future__ import annotations

import json
from typing import Any

from backend.scanners.base_scanner import BaseScanner
from backend.scanners.parsers import parse_nuclei_output


class NucleiScanner(BaseScanner):
    def validate_target(self, target: str) -> bool:
        # allow URLs and hosts
        t = self.sanitize_target(target)
        return bool(t)

    async def run(self, target: str) -> dict[str, Any]:
        if not self.validate_target(target):
            raise ValueError("Invalid target")

        sanitized = self.sanitize_target(target)
        # Added -severity info to ensure only non-aggressive recon templates are run
        # Added -rl 20 to enforce rate limiting and prevent aggressive traffic
        cmd = ["nuclei", "-u", sanitized, "-json", "-severity", "info", "-rl", "20"]
        stdout, stderr = await self.execute_subprocess(cmd)
        # nuclei may output multiple json objects per line; parse robustly
        parsed = parse_nuclei_output(stdout)
        return {"target": sanitized, "findings": parsed, "raw": stdout, "stderr": stderr}

    def parse_output(self, output: str) -> list[dict[str, Any]]:
        return parse_nuclei_output(output)
