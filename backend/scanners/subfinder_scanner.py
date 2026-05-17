"""
Subfinder scanner for subdomain discovery.
Secure async execution with target validation.
"""
import logging
from typing import Any

from backend.scanners.base_scanner import BaseScanner

logger = logging.getLogger(__name__)


class SubfinderScanner(BaseScanner):
    """
    Subfinder scanner for passive subdomain enumeration.
    Discovers subdomains of target domain.
    """

    def __init__(self, timeout: int = 300):
        """Initialize Subfinder scanner."""
        super().__init__(timeout=timeout)

    def validate_target(self, target: str) -> bool:
        """
        Validate domain target format.

        Args:
            target: Domain to validate (e.g., example.com)

        Returns:
            True if valid domain format
        """
        # Basic domain validation
        target = target.strip().lower()
        if not target or len(target) > 255:
            logger.warning(f"Invalid target: {target}")
            return False

        # Must be valid domain format
        parts = target.split(".")
        if len(parts) < 2:
            logger.warning(f"Target missing TLD: {target}")
            return False

        # Each part must be alphanumeric with hyphens
        for part in parts:
            if not part or not all(c.isalnum() or c == "-" for c in part):
                logger.warning(f"Invalid domain part: {part}")
                return False

        return True

    async def run(self, target: str) -> dict[str, Any]:
        """
        Execute Subfinder scan.

        Args:
            target: Domain to scan

        Returns:
            Dictionary with subdomains and metadata
        """
        if not self.validate_target(target):
            logger.error(f"Invalid target for subfinder: {target}")
            return {
                "status": "failed",
                "target": target,
                "results": [],
                "error": "Invalid target format",
            }

        target = self.sanitize_target(target)

        try:
            logger.info(f"Starting Subfinder scan on {target}")

            # Build command: subfinder -d target -silent
            # -silent: Silent mode (no banners/info)
            command = ["subfinder", "-d", target, "-silent"]

            stdout, stderr = await self.execute_subprocess(command)

            subdomains = self.parse_output(stdout)

            logger.info(
                f"Subfinder found {len(subdomains)} subdomains for {target}"
            )

            return {
                "status": "success",
                "target": target,
                "scanner": "subfinder",
                "results": subdomains,
                "count": len(subdomains),
                "stderr": stderr if stderr else None,
            }

        except TimeoutError as exc:
            logger.error(f"Subfinder timeout: {exc}")
            return {
                "status": "timeout",
                "target": target,
                "results": [],
                "error": str(exc),
            }

        except RuntimeError as exc:
            logger.error(f"Subfinder failed: {exc}")
            return {
                "status": "failed",
                "target": target,
                "results": [],
                "error": str(exc),
            }

    def parse_output(self, output: str) -> list[str]:
        """
        Parse Subfinder output into list of subdomains.

        Args:
            output: Raw Subfinder output (one subdomain per line)

        Returns:
            List of discovered subdomains
        """
        if not output:
            return []

        subdomains = []
        for line in output.strip().split("\n"):
            subdomain = line.strip()
            # Filter out empty lines and invalid entries
            if subdomain and "." in subdomain and len(subdomain) <= 255:
                subdomains.append(subdomain)

        # Remove duplicates while preserving order
        seen = set()
        unique_subdomains = []
        for subdomain in subdomains:
            if subdomain not in seen:
                seen.add(subdomain)
                unique_subdomains.append(subdomain)

        return unique_subdomains
