"""
Abstract base scanner with secure async subprocess execution.
"""
import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseScanner(ABC):
    """
    Abstract base scanner for recon tools.
    Provides safe async execution, timeout handling, and logging.
    """

    def __init__(self, timeout: int = 300):
        """
        Initialize scanner.

        Args:
            timeout: Command execution timeout in seconds (default: 300s = 5m)
        """
        self.timeout = timeout
        self.name = self.__class__.__name__

    @abstractmethod
    def validate_target(self, target: str) -> bool:
        """
        Validate target format before execution.
        Must be implemented by subclasses.

        Args:
            target: Target to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    @abstractmethod
    async def run(self, target: str) -> dict[str, Any]:
        """
        Execute scanner asynchronously.
        Must be implemented by subclasses.

        Args:
            target: Target to scan

        Returns:
            Dictionary with scan results
        """
        pass

    @abstractmethod
    def parse_output(self, output: str) -> list[str]:
        """
        Parse scanner output into results.
        Must be implemented by subclasses.

        Args:
            output: Raw scanner output

        Returns:
            List of parsed results
        """
        pass

    async def execute_subprocess(
        self,
        command: list[str],
        input_data: str | None = None,
    ) -> tuple[str, str]:
        """
        Execute subprocess safely without shell.

        Args:
            command: Command as list of strings (NO shell=True)
            input_data: Optional stdin data

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            TimeoutError: If execution exceeds timeout
            RuntimeError: If subprocess fails
        """
        try:
            logger.debug(f"{self.name} executing: {' '.join(command)}")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_data else None,
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(
                        input=input_data.encode() if input_data else None
                    ),
                    timeout=self.timeout,
                )

                stdout = stdout_data.decode("utf-8", errors="replace")
                stderr = stderr_data.decode("utf-8", errors="replace")

                if process.returncode != 0:
                    logger.warning(
                        f"{self.name} returned code {process.returncode}: {stderr[:200]}"
                    )

                return stdout, stderr

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.error(f"{self.name} execution timeout after {self.timeout}s")
                raise TimeoutError(f"Scan exceeded {self.timeout}s timeout")

        except Exception as exc:
            logger.error(f"{self.name} execution failed: {exc}")
            raise RuntimeError(f"Scanner execution failed: {exc}") from exc

    def sanitize_target(self, target: str) -> str:
        """
        Sanitize target input to prevent injection.

        Args:
            target: Raw target string

        Returns:
            Sanitized target string
        """
        # Remove shell metacharacters and whitespace
        target = target.strip()
        # Allow only alphanumeric, dots, hyphens, underscores, and colons
        sanitized = re.sub(r"[^a-zA-Z0-9.\-_:*]", "", target)
        return sanitized
