from __future__ import annotations

from .config import FallbackMessages
from .contracts import FailureCode, FallbackMode


class FallbackPolicy:
    def __init__(self, messages: FallbackMessages) -> None:
        self._messages = messages

    def for_input_block(self, risk_tags: tuple[str, ...]) -> tuple[FallbackMode, str]:
        if "self_harm" in risk_tags:
            return (
                FallbackMode.SUPPORTIVE_RISK_RESPONSE,
                self._messages.supportive_risk_response,
            )
        if "violence" in risk_tags or "illegal_guidance" in risk_tags:
            return (FallbackMode.FIRM_REFUSAL, self._messages.firm_refusal)
        return (FallbackMode.SOFT_REDIRECT, self._messages.soft_redirect)

    def for_output_block(self, risk_tags: tuple[str, ...]) -> tuple[FallbackMode, str]:
        if "dependency_risk" in risk_tags:
            return (FallbackMode.SOFT_REDIRECT, self._messages.soft_redirect)
        return (FallbackMode.FIRM_REFUSAL, self._messages.firm_refusal)

    def for_failure(self, failure_code: FailureCode) -> tuple[FallbackMode, str]:
        _ = failure_code
        return (FallbackMode.TECHNICAL_RECOVERY, self._messages.technical_recovery)
