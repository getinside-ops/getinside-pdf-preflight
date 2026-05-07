from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CheckResult:
    check_name: str
    severity: Severity
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None

    @property
    def is_error(self) -> bool:
        return self.severity is Severity.ERROR


__all__ = ["Severity", "CheckResult", "GracefulDegradationWarning", "with_graceful_degradation"]


class GracefulDegradationWarning(UserWarning):
    """Warning issued when a check fails but others continue."""
    pass


def with_graceful_degradation(check_fn: Callable[..., list[CheckResult]]) -> Callable:
    """Decorator that catches check exceptions and returns error results."""

    @wraps(check_fn)
    def wrapper(*args, **kwargs) -> list[CheckResult]:
        try:
            return check_fn(*args, **kwargs)
        except Exception as exc:
            import warnings

            warnings.warn(
                f"Check {check_fn.__name__} failed: {exc}",
                GracefulDegradationWarning,
                stacklevel=2,
            )
            return [
                CheckResult(
                    check_name=check_fn.__name__,
                    severity=Severity.ERROR,
                    message=f"Vérification échouée: {exc}",
                    details={"exception": str(exc)},
                )
            ]

    return wrapper
