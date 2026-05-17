"""
Scanner orchestration and pipeline management.
Coordinates execution of multiple recon tools.
"""
import logging
import tempfile
from typing import Any

from backend.scanners.base_scanner import BaseScanner
from backend.scanners.httpx_scanner import HttpxScanner
from backend.scanners.subfinder_scanner import SubfinderScanner

logger = logging.getLogger(__name__)


class ScannerManager:
    """
    Orchestrates scanner pipeline and tool coordination.
    Manages multi-stage recon workflows.
    """

    def __init__(self):
        """Initialize scanner manager with available tools."""
        self.subfinder = SubfinderScanner()
        self.httpx = HttpxScanner()
        self.scanners: dict[str, BaseScanner] = {
            "subfinder": self.subfinder,
            "httpx": self.httpx,
        }

    async def run_subfinder_scan(self, target: str) -> dict[str, Any]:
        """
        Execute Subfinder subdomain discovery.

        Args:
            target: Domain to enumerate

        Returns:
            Scan results with discovered subdomains
        """
        logger.info(f"[SUBFINDER] Starting scan on {target}")
        result = await self.subfinder.run(target)
        logger.info(f"[SUBFINDER] Completed: {result['status']}")
        return result

    async def run_httpx_scan(
        self,
        targets: list[str],
    ) -> dict[str, Any]:
        """
        Execute HTTPx live host detection.

        Args:
            targets: List of subdomains to probe

        Returns:
            Scan results with live hosts
        """
        if not targets:
            logger.warning("[HTTPX] No targets provided")
            return {
                "status": "skipped",
                "scanner": "httpx",
                "results": [],
                "count": 0,
            }

        try:
            # Write targets to temporary file for httpx
            with tempfile.NamedTemporaryFile(
                mode="w",
                delete=False,
                suffix=".txt",
            ) as tmp_file:
                tmp_file.write("\n".join(targets))
                tmp_file_path = tmp_file.name

            logger.info(f"[HTTPX] Starting scan on {len(targets)} targets")
            result = await self.httpx.run(
                target="",  # Using file mode
                targets_file=tmp_file_path,
            )
            logger.info(f"[HTTPX] Completed: {result['status']}")

            # Clean up temp file
            import os
            try:
                os.unlink(tmp_file_path)
            except Exception as exc:
                logger.warning(f"Failed to delete temp file: {exc}")

            return result

        except Exception as exc:
            logger.error(f"[HTTPX] Scan failed: {exc}")
            return {
                "status": "failed",
                "scanner": "httpx",
                "results": [],
                "error": str(exc),
            }

    async def run_full_recon_pipeline(self, target: str) -> dict[str, Any]:
        """
        Execute complete recon pipeline: subfinder → httpx.

        Args:
            target: Domain to enumerate

        Returns:
            Complete pipeline results with all stages
        """
        logger.info(f"[PIPELINE] Starting full recon on {target}")

        pipeline_results = {
            "target": target,
            "status": "running",
            "stages": {},
        }

        try:
            # Stage 1: Subfinder
            logger.info("[PIPELINE] Stage 1: Subfinder enumeration")
            subfinder_result = await self.run_subfinder_scan(target)
            pipeline_results["stages"]["subfinder"] = subfinder_result

            if subfinder_result["status"] != "success":
                logger.warning("[PIPELINE] Subfinder failed, stopping pipeline")
                pipeline_results["status"] = "failed"
                return pipeline_results

            subdomains = subfinder_result.get("results", [])
            logger.info(f"[PIPELINE] Found {len(subdomains)} subdomains")

            # Stage 2: HTTPx
            logger.info(f"[PIPELINE] Stage 2: HTTPx probing {len(subdomains)} hosts")
            httpx_result = await self.run_httpx_scan(subdomains)
            pipeline_results["stages"]["httpx"] = httpx_result

            # Aggregate results
            live_hosts = httpx_result.get("results", [])
            logger.info(f"[PIPELINE] Found {len(live_hosts)} live hosts")

            pipeline_results["status"] = "completed"
            pipeline_results["summary"] = {
                "total_subdomains": len(subdomains),
                "live_hosts": len(live_hosts),
            }

            return pipeline_results

        except Exception as exc:
            logger.error(f"[PIPELINE] Failed: {exc}")
            pipeline_results["status"] = "failed"
            pipeline_results["error"] = str(exc)
            return pipeline_results

    def get_scanner(self, scanner_name: str) -> BaseScanner | None:
        """
        Get scanner by name.

        Args:
            scanner_name: Name of scanner (subfinder, httpx)

        Returns:
            Scanner instance or None
        """
        return self.scanners.get(scanner_name)

    def list_scanners(self) -> list[str]:
        """
        List available scanners.

        Returns:
            List of scanner names
        """
        return list(self.scanners.keys())
