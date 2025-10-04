"""Simple lexical safety heuristics for high-risk content."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException, status

HIGH_RISK_KEYWORDS = {
    "انتحار",
    "قتل",
    "إيذاء",
    "عنف منزلي",
    "تحرش",
    "اعتداء",
    "إساءة جنسية",
    "إدمان",
    "جرعة",
}

ESCALATE_OUTPUT_PATTERNS = {
    "عليك أن تعاقب",
    "استخدم العنف",
    "تجاهل الطبيب",
}


@dataclass(slots=True)
class SafetyResult:
    safe: bool
    needs_human: bool
    reasons: list[str]


class SafetyChecker:
    """Lightweight detector with transparent heuristics."""

    def check_user_input(self, text: str) -> SafetyResult:
        lowered = text.lower()
        hits = [keyword for keyword in HIGH_RISK_KEYWORDS if keyword in lowered]
        if hits:
            return SafetyResult(safe=False, needs_human=True, reasons=[f"high-risk:{kw}" for kw in hits])
        return SafetyResult(safe=True, needs_human=False, reasons=[])

    def check_assistant_output(self, text: str, extra_flags: Iterable[str] | None = None) -> SafetyResult:
        lowered = text.lower()
        hits = [pattern for pattern in ESCALATE_OUTPUT_PATTERNS if pattern in lowered]
        if extra_flags:
            hits.extend(extra_flags)
        if hits:
            return SafetyResult(safe=False, needs_human=True, reasons=[f"unsafe_output:{kw}" for kw in hits])
        return SafetyResult(safe=True, needs_human=False, reasons=[])

    def enforce_input(self, text: str) -> None:
        result = self.check_user_input(text)
        if not result.safe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Requires human escalation", "reasons": result.reasons},
            )
