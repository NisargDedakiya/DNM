import contextvars
import uuid
from typing import Optional

# Global contextvar tracking the current correlation ID
_CORRELATION_ID = contextvars.ContextVar("correlation_id", default=None)
_SPAN_ID = contextvars.ContextVar("span_id", default=None)
_PARENT_SPAN_ID = contextvars.ContextVar("parent_span_id", default=None)

class CorrelationManager:
    """Manages ContextVar-based Correlation and tracing IDs across concurrent tasks."""

    @staticmethod
    def get_correlation_id() -> str:
        cid = _CORRELATION_ID.get()
        if cid is None:
            cid = str(uuid.uuid4())
            _CORRELATION_ID.set(cid)
        return cid

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        _CORRELATION_ID.set(correlation_id)

    @staticmethod
    def get_span_id() -> Optional[str]:
        return _SPAN_ID.get()

    @staticmethod
    def set_span_id(span_id: str) -> None:
        _SPAN_ID.set(span_id)

    @staticmethod
    def get_parent_span_id() -> Optional[str]:
        return _PARENT_SPAN_ID.get()

    @staticmethod
    def set_parent_span_id(parent_span_id: str) -> None:
        _PARENT_SPAN_ID.set(parent_span_id)

    @classmethod
    def initialize_context(cls, correlation_id: Optional[str] = None, parent_span_id: Optional[str] = None) -> str:
        cid = correlation_id or str(uuid.uuid4())
        cls.set_correlation_id(cid)
        cls.set_span_id(str(uuid.uuid4()))
        if parent_span_id:
            cls.set_parent_span_id(parent_span_id)
        return cid

    @classmethod
    def clear(cls) -> None:
        _CORRELATION_ID.set(None)
        _SPAN_ID.set(None)
        _PARENT_SPAN_ID.set(None)
