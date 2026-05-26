"""
Safe recon tool execution sandbox for distributed workers.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_TOOLS = {"subfinder", "httpx", "katana", "nuclei", "ffuf", "dalfox"}


class TaskExecutor:
    """Executes recon tools with shell-free subprocesses and timeouts."""

    def __init__(self, timeout_seconds: int = 900, max_retries: int = 2):
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def execute_tool(self, tool_name: str, args: list[str]) -> dict[str, Any]:
        tool = tool_name.lower().strip()
        if tool not in SUPPORTED_TOOLS:
            raise ValueError(f"Unsupported tool: {tool_name}")

        executable = shutil.which(tool)
        if not executable:
            return {
                "tool": tool,
                "status": "unavailable",
                "stdout": "",
                "stderr": f"{tool} not installed on worker",
                "return_code": 127,
            }

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                process = await asyncio.create_subprocess_exec(
                    executable,
                    *[str(arg) for arg in args],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=self.timeout_seconds)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise TimeoutError(f"{tool} timed out after {self.timeout_seconds}s")

                stdout = stdout_bytes.decode(errors="ignore") if stdout_bytes else ""
                stderr = stderr_bytes.decode(errors="ignore") if stderr_bytes else ""
                return {
                    "tool": tool,
                    "status": "completed" if process.returncode == 0 else "failed",
                    "stdout": stdout[:20000],
                    "stderr": stderr[:12000],
                    "return_code": process.returncode,
                    "attempt": attempt + 1,
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Tool execution failed for %s (attempt %s): %s", tool, attempt + 1, exc)
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(min(2 ** attempt, 8))

        return {
            "tool": tool,
            "status": "failed",
            "stdout": "",
            "stderr": last_error or "execution failed",
            "return_code": 1,
        }

