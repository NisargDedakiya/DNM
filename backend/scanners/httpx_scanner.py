"""
HTTPx scanner for live host detection.
Checks HTTP/HTTPS responsiveness of targets.
"""
import logging
from typing import Any

from backend.scanners.base_scanner import BaseScanner

logger = logging.getLogger(__name__)


class HttpxScanner(BaseScanner):
    """
    HTTPx scanner for probing live web services.
    Detects responsive hosts and captures HTTP metadata.
    """

    def __init__(self, timeout: int = 300):
        """Initialize HTTPx scanner."""
        super().__init__(timeout=timeout)

    def validate_target(self, target: str) -> bool:
        """
        Validate target for HTTPx (domain or list).

        Args:
            target: Domain or filename containing list

        Returns:
            True if valid
        """
        target = target.strip()
        if not target or len(target) > 1000:
            logger.warning(f"Invalid target: {target}")
            return False

        # Allow domain or filepath reference
        return True

    async def run(self, target: str, targets_file: str | None = None) -> dict[str, Any]:
        """
        Execute HTTPx scan on targets.

        Args:
            target: Single domain or host
            targets_file: Optional file path with list of targets

        Returns:
            Dictionary with live hosts and metadata
        """
        if not self.validate_target(target):
            logger.error(f"Invalid target for httpx: {target}")
            return {
                "status": "failed",
                "target": target,
                "results": [],
                "error": "Invalid target format",
            }

        target = self.sanitize_target(target)

        try:
            logger.info(f"Starting HTTPx scan on {target}")

            # Build command: httpx -silent [other flags]
            # -silent: Silent mode (minimal output)
            # -json: JSON output for parsing
            command = ["httpx", "-silent", "-json"]

            # Add target as stdin or argument
            if targets_file:
                # If targets come from file
                command.extend(["-l", targets_file])
                input_data = None
            else:
                # Single target via stdin
                input_data = target

            stdout, stderr = await self.execute_subprocess(
                command,
                input_data=input_data,
            )

            results = self.parse_output(stdout)

            logger.info(
                f"HTTPx found {len(results)} live hosts for {target}"
            )

            return {
                "status": "success",
                "target": target,
                "scanner": "httpx",
                "results": results,
                "count": len(results),
                "stderr": stderr if stderr else None,
            }

        except TimeoutError as exc:
            logger.error(f"HTTPx timeout: {exc}")
            return {
                "status": "timeout",
                "target": target,
                "results": [],
                "error": str(exc),
            }

        except RuntimeError as exc:
            logger.error(f"HTTPx failed: {exc}")
            return {
                "status": "failed",
                "target": target,
                "results": [],
                "error": str(exc),
            }

    def parse_output(self, output: str) -> list[dict[str, Any]]:
        """
        Parse HTTPx JSON output into structured results.

        Args:
            output: Raw HTTPx output (JSON lines format)

        Returns:
            List of host objects with HTTP metadata
        """
        if not output:
            return []

        import json

        results = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
                # Extract key fields from HTTPx JSON output
                host_data = {
                    "url": entry.get("url", ""),
                    "status_code": entry.get("status_code"),
                    "title": entry.get("title", ""),
                    "content_length": entry.get("content_length"),
                    "time": entry.get("time"),
                    "port": entry.get("port"),
                    "scheme": entry.get("scheme"),
                }
                results.append(host_data)

            except json.JSONDecodeError as exc:
                logger.warning(f"Failed to parse HTTPx JSON line: {line[:100]}")
                continue

        return results
