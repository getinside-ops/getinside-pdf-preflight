from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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

    @property
    def is_error(self) -> bool:
        return self.severity is Severity.ERROR


__all__ = ["Severity", "CheckResult"]
