"""
Katana scanner integration using BaseScanner for safe async subprocess execution.
"""
from __future__ import annotations

import re
from typing import Any

from backend.scanners.base_scanner import BaseScanner
from backend.scanners.parsers import parse_katana_output


class KatanaScanner(BaseScanner):
    def validate_target(self, target: str) -> bool:
        # basic hostname/url validation
        t = self.sanitize_target(target)
        # allow hostnames, IPs, and http(s) urls
        return bool(re.match(r"^(https?://)?[a-zA-Z0-9.\-_:]+$", t))

    async def run(self, target: str) -> dict[str, Any]:
        if not self.validate_target(target):
            raise ValueError("Invalid target")

        sanitized = self.sanitize_target(target)
        cmd = ["katana", "-u", sanitized, "-silent"]
        stdout, stderr = await self.execute_subprocess(cmd)
        results = parse_katana_output(stdout)
        return {"target": sanitized, "endpoints": results, "raw": stdout, "stderr": stderr}

    def parse_output(self, output: str) -> list[str]:
        return parse_katana_output(output)
