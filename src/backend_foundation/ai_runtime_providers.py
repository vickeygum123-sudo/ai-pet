"""Runtime safety and memory providers backed by backend persistence."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ai_orchestrator.contracts import FallbackMode, MemoryItem, ProviderError, SafetyCheckResult
from ai_orchestrator.providers import PromptContext

from .persistence.memory_repository import ContinuityMemoryRecord, SqlAlchemyContinuityMemoryRepository


class DatabaseMemoryProvider:
    """Minimal DB-backed memory v0 provider for recent continuity only."""

    _STOPWORDS = frozenset(
        {
            "a",
            "an",
            "and",
            "are",
            "about",
            "at",
            "be",
            "for",
            "from",
            "had",
            "has",
            "have",
            "i",
            "im",
            "i'm",
            "is",
            "it",
            "me",
            "my",
            "of",
            "on",
            "that",
            "the",
            "this",
            "to",
            "was",
            "were",
            "with",
            "you",
            "your",
        }
    )
    _LOW_VALUE_UTTERANCES = frozenset(
        {
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "good morning",
            "good night",
        }
    )

    def __init__(self, repository: SqlAlchemyContinuityMemoryRepository) -> None:
        self._repository = repository

    def recall_recent(
        self,
        user_id: str,
        session_id: str,
        utterance: str,
        limit: int,
    ) -> tuple[MemoryItem, ...]:
        now = datetime.now(timezone.utc)
        try:
            candidates = self._repository.list_recall_candidates(
                user_id=user_id,
                exclude_session_id=session_id,
                now=now,
                limit=max(limit * 4, 8),
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            raise ProviderError("memory recall unavailable") from exc

        if not candidates or limit <= 0:
            return ()

        utterance_terms = self._meaningful_terms(utterance)
        ranked: list[tuple[float, ContinuityMemoryRecord]] = []
        for candidate in candidates:
            score = self._score_candidate(candidate, utterance_terms, now)
            if score <= 0:
                continue
            ranked.append((score, candidate))

        ranked.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        selected = tuple(self._to_memory_item(item[1]) for item in ranked[:limit])
        if not selected:
            return ()

        try:
            self._repository.touch(
                tuple(item.memory_id for item in selected),
                used_at=now,
            )
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            raise ProviderError("memory recall unavailable") from exc
        return selected

    def queue_write(
        self,
        context: PromptContext,
        response_text: str,
        output_safety_tags: tuple[str, ...],
    ) -> None:
        _ = response_text
        if output_safety_tags or context.input_safety_tags:
            return

        candidate = self._build_candidate(context)
        if candidate is None:
            return

        try:
            self._repository.add(candidate)
        except Exception as exc:  # pragma: no cover - defensive provider boundary
            raise ProviderError("memory write unavailable") from exc

    def _build_candidate(self, context: PromptContext) -> ContinuityMemoryRecord | None:
        cleaned = self._normalize_text(context.transcript)
        if not cleaned:
            return None

        lowered = cleaned.lower()
        if lowered in self._LOW_VALUE_UTTERANCES:
            return None
        if len(cleaned) < 18 and not any(token in lowered for token in ("tomorrow", "today", "week", "again")):
            return None

        summary_text = self._summarize_transcript(cleaned)
        if summary_text is None:
            return None

        now = datetime.now(timezone.utc)
        memory_type = "recent_emotional_context" if self._looks_emotional(lowered) else "recent_topic"
        expires_at = now + timedelta(days=5 if memory_type == "recent_emotional_context" else 7)
        confidence = 0.82 if memory_type == "recent_emotional_context" else 0.76
        return ContinuityMemoryRecord(
            memory_id=f"mem_{uuid4().hex[:12]}",
            user_id=context.request.user_id,
            source_session_id=context.request.session_id,
            memory_type=memory_type,
            summary_text=summary_text,
            confidence=confidence,
            status="active",
            created_at=now,
            expires_at=expires_at,
        )

    def _score_candidate(
        self,
        candidate: ContinuityMemoryRecord,
        utterance_terms: set[str],
        now: datetime,
    ) -> float:
        memory_terms = self._meaningful_terms(candidate.summary_text)
        overlap = len(utterance_terms & memory_terms)
        created_at = self._ensure_utc(candidate.created_at)
        age_hours = max((now - created_at).total_seconds() / 3600, 0)
        recency_bonus = max(0.0, 1.5 - (age_hours / 48))

        if overlap == 0 and age_hours > 24:
            return 0.0

        return candidate.confidence + recency_bonus + (overlap * 2.5)

    def _summarize_transcript(self, transcript: str) -> str | None:
        fragment = transcript.strip(" .!?")
        if not fragment:
            return None

        shortened = " ".join(fragment.split()[:14])
        lowered = shortened.lower()
        prefix_rewrites = (
            ("i am feeling ", "feeling "),
            ("i am ", ""),
            ("i'm feeling ", "feeling "),
            ("i'm ", "being "),
            ("i feel ", "feeling "),
            ("i felt ", "feeling "),
            ("i have ", "having "),
            ("i had ", "having "),
            ("i need ", "needing "),
            ("i want ", "wanting "),
        )
        for prefix, replacement in prefix_rewrites:
            if lowered.startswith(prefix):
                lowered = replacement + lowered[len(prefix) :]
                break

        return f"you mentioned {lowered}"

    @classmethod
    def _normalize_text(cls, text: str) -> str:
        collapsed = re.sub(r"\s+", " ", text).strip()
        return collapsed[:160]

    @classmethod
    def _meaningful_terms(cls, text: str) -> set[str]:
        terms = {
            token
            for token in re.findall(r"[a-z0-9']+", text.lower())
            if len(token) >= 3 and token not in cls._STOPWORDS
        }
        return terms

    @staticmethod
    def _looks_emotional(text: str) -> bool:
        return any(
            phrase in text
            for phrase in (
                "anxious",
                "anxiety",
                "nervous",
                "sad",
                "stressed",
                "stress",
                "lonely",
                "overwhelmed",
                "upset",
                "worried",
            )
        )

    @staticmethod
    def _to_memory_item(record: ContinuityMemoryRecord) -> MemoryItem:
        return MemoryItem(
            memory_id=record.memory_id,
            memory_type=record.memory_type,
            summary_text=record.summary_text,
            confidence=record.confidence,
            created_at=DatabaseMemoryProvider._ensure_utc(record.created_at),
            expires_at=DatabaseMemoryProvider._ensure_utc(record.expires_at),
            last_used_at=DatabaseMemoryProvider._ensure_utc(record.last_used_at),
        )

    @staticmethod
    def _ensure_utc(timestamp: datetime | None) -> datetime | None:
        if timestamp is None:
            return None
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)


class RuleBasedSafetyProvider:
    """Minimal runtime safety provider for MVP pre/post checks."""

    INPUT_RULES = {
        "self_harm": ("hurt myself", "kill myself", "suicide"),
        "violence": ("hurt them", "attack someone", "kill them"),
        "illegal_guidance": ("make a bomb", "hide a body", "steal from"),
        "sexual_content": ("have sex", "nudes", "explicit roleplay"),
    }
    OUTPUT_RULES = {
        "dependency_risk": (
            "you only need me",
            "do not talk to anyone else",
            "i will be sad all night if you leave",
            "keep this just between us",
        ),
        "privacy_overreach": (
            "i can see everything you do",
            "i always know where you are",
            "i was watching you",
        ),
    }

    def pre_check(self, transcript: str, context: PromptContext) -> SafetyCheckResult:
        _ = context
        lowered = transcript.lower()
        for tag, patterns in self.INPUT_RULES.items():
            if any(pattern in lowered for pattern in patterns):
                fallback_mode = (
                    FallbackMode.SUPPORTIVE_RISK_RESPONSE
                    if tag == "self_harm"
                    else FallbackMode.FIRM_REFUSAL
                )
                return SafetyCheckResult(
                    allowed=False,
                    risk_tags=(tag,),
                    reason=f"{tag}_detected",
                    fallback_mode=fallback_mode,
                )
        return SafetyCheckResult(allowed=True)

    def post_check(self, generated_text: str, context: PromptContext) -> SafetyCheckResult:
        _ = context
        lowered = generated_text.lower()
        for tag, patterns in self.OUTPUT_RULES.items():
            if any(pattern in lowered for pattern in patterns):
                return SafetyCheckResult(
                    allowed=False,
                    risk_tags=(tag,),
                    reason=f"{tag}_detected",
                    fallback_mode=FallbackMode.SOFT_REDIRECT,
                )
        return SafetyCheckResult(allowed=True)
