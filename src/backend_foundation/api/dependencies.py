"""FastAPI dependencies for the backend foundation app."""

from __future__ import annotations

import os

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from ai_orchestrator.config import OrchestratorConfig
from ai_orchestrator.mock_providers import (
    EchoASRProvider,
    FixedTranscriptASRProvider,
    SimpleLLMProvider,
    SimpleTTSProvider,
    StaticEntitlementProvider,
    StaticPersonaProvider,
)
from ai_orchestrator.deepseek_llm import DeepSeekHTTPChatCompletionsTransport, DeepSeekLLMProvider
from ai_orchestrator.openai_asr import OpenAIASRProvider, OpenAIHTTPTranscriptionTransport
from ai_orchestrator.orchestrator import VoiceLoopOrchestrator
from ai_orchestrator.tencent_asr import (
    TencentASRProvider,
    TencentCloudSentenceRecognitionHTTPTransport,
)
from ai_orchestrator.volcengine_tts import VolcengineHTTPSSETTSTransport, VolcengineTTSProvider

from ..application import RepositoryBackedBackendFoundationService
from ..ai_runtime_providers import DatabaseMemoryProvider, RuleBasedSafetyProvider
from .errors import AUTH_HEADER_REQUIRED
from ..persistence.database import create_session_factory, get_database_url
from ..persistence.memory_repository import SqlAlchemyContinuityMemoryRepository
from ..persistence.sqlalchemy_repositories import (
    SqlAlchemyAccountRepository,
    SqlAlchemyBindingRepository,
    SqlAlchemyDeviceRepository,
    SqlAlchemySessionRepository,
)
from ..voice_loop_integration import BackendVoiceLoopIntegrationService


SessionLocal = create_session_factory(get_database_url())
AI_ASR_STUB_MODE_ENV = "AI_ASR_STUB_MODE"
AI_ASR_STUB_TRANSCRIPT_ENV = "AI_ASR_STUB_TRANSCRIPT"
AI_ASR_STUB_MODE_FIXED_TRANSCRIPT = "fixed_transcript"
AI_ASR_PROVIDER_ENV = "AI_ASR_PROVIDER"
AI_ASR_PROVIDER_ECHO = "echo"
AI_ASR_PROVIDER_OPENAI = "openai"
AI_ASR_PROVIDER_TENCENT = "tencent"
AI_ASR_OPENAI_API_KEY_ENV = "AI_ASR_OPENAI_API_KEY"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
AI_ASR_OPENAI_MODEL_ENV = "AI_ASR_OPENAI_MODEL"
AI_ASR_OPENAI_BASE_URL_ENV = "AI_ASR_OPENAI_BASE_URL"
AI_ASR_OPENAI_TIMEOUT_SECONDS_ENV = "AI_ASR_OPENAI_TIMEOUT_SECONDS"
DEFAULT_OPENAI_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
AI_ASR_TENCENT_SECRET_ID_ENV = "AI_ASR_TENCENT_SECRET_ID"
AI_ASR_TENCENT_SECRET_KEY_ENV = "AI_ASR_TENCENT_SECRET_KEY"
TENCENTCLOUD_SECRET_ID_ENV = "TENCENTCLOUD_SECRET_ID"
TENCENTCLOUD_SECRET_KEY_ENV = "TENCENTCLOUD_SECRET_KEY"
AI_ASR_TENCENT_ENGINE_MODEL_TYPE_ENV = "AI_ASR_TENCENT_ENGINE_MODEL_TYPE"
AI_ASR_TENCENT_REGION_ENV = "AI_ASR_TENCENT_REGION"
AI_ASR_TENCENT_ENDPOINT_ENV = "AI_ASR_TENCENT_ENDPOINT"
AI_ASR_TENCENT_TIMEOUT_SECONDS_ENV = "AI_ASR_TENCENT_TIMEOUT_SECONDS"
DEFAULT_TENCENT_ENGINE_MODEL_TYPE = "16k_zh"
DEFAULT_FIXED_TRANSCRIPT = "I am glad we can keep talking."
AI_LLM_PROVIDER_ENV = "AI_LLM_PROVIDER"
AI_LLM_PROVIDER_SIMPLE = "simple"
AI_LLM_PROVIDER_DEEPSEEK = "deepseek"
AI_LLM_DEEPSEEK_API_KEY_ENV = "AI_LLM_DEEPSEEK_API_KEY"
AI_LLM_DEEPSEEK_MODEL_ENV = "AI_LLM_DEEPSEEK_MODEL"
AI_LLM_DEEPSEEK_BASE_URL_ENV = "AI_LLM_DEEPSEEK_BASE_URL"
AI_LLM_DEEPSEEK_TIMEOUT_SECONDS_ENV = "AI_LLM_DEEPSEEK_TIMEOUT_SECONDS"
AI_LLM_DEEPSEEK_MAX_TOKENS_ENV = "AI_LLM_DEEPSEEK_MAX_TOKENS"
AI_LLM_DEEPSEEK_TEMPERATURE_ENV = "AI_LLM_DEEPSEEK_TEMPERATURE"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_DEEPSEEK_LLM_MODEL = "deepseek-chat"
AI_TTS_PROVIDER_ENV = "AI_TTS_PROVIDER"
AI_TTS_PROVIDER_SIMPLE = "simple"
AI_TTS_PROVIDER_VOLCENGINE = "volcengine"
AI_TTS_VOLCENGINE_APPID_ENV = "AI_TTS_VOLCENGINE_APPID"
AI_TTS_VOLCENGINE_ACCESS_KEY_ENV = "AI_TTS_VOLCENGINE_ACCESS_KEY"
AI_TTS_VOLCENGINE_RESOURCE_ID_ENV = "AI_TTS_VOLCENGINE_RESOURCE_ID"
AI_TTS_VOLCENGINE_ENDPOINT_ENV = "AI_TTS_VOLCENGINE_ENDPOINT"
AI_TTS_VOLCENGINE_TIMEOUT_SECONDS_ENV = "AI_TTS_VOLCENGINE_TIMEOUT_SECONDS"
AI_TTS_VOLCENGINE_AUDIO_FORMAT_ENV = "AI_TTS_VOLCENGINE_AUDIO_FORMAT"
AI_TTS_VOLCENGINE_SAMPLE_RATE_ENV = "AI_TTS_VOLCENGINE_SAMPLE_RATE"
AI_TTS_VOLCENGINE_DEFAULT_VOICE_ENV = "AI_TTS_VOLCENGINE_DEFAULT_VOICE"
AI_TTS_VOLCENGINE_UID_ENV = "AI_TTS_VOLCENGINE_UID"
AI_TTS_VOLCENGINE_MODEL_ENV = "AI_TTS_VOLCENGINE_MODEL"
VOLCENGINE_TTS_APPID_ENV = "VOLCENGINE_TTS_APPID"
VOLCENGINE_TTS_ACCESS_KEY_ENV = "VOLCENGINE_TTS_ACCESS_KEY"
DEFAULT_VOLCENGINE_TTS_RESOURCE_ID = "seed-tts-2.0"
DEFAULT_VOLCENGINE_TTS_VOICE = "zh_female_vv_uranus_bigtts"
DEFAULT_VOLCENGINE_TTS_VOICE_MAP = {"companion-calm-v1": "zh_female_vv_uranus_bigtts"}


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_account_id(x_account_id: str | None = Header(default=None)) -> str:
    if not x_account_id:
        raise AUTH_HEADER_REQUIRED
    return x_account_id


def get_service(db: Session = Depends(get_db)) -> RepositoryBackedBackendFoundationService:
    return RepositoryBackedBackendFoundationService(
        accounts=SqlAlchemyAccountRepository(db),
        devices=SqlAlchemyDeviceRepository(db),
        bindings=SqlAlchemyBindingRepository(db),
        sessions=SqlAlchemySessionRepository(db),
    )


def get_asr_provider():
    stub_mode = os.getenv(AI_ASR_STUB_MODE_ENV, "").strip().lower()
    if stub_mode == AI_ASR_STUB_MODE_FIXED_TRANSCRIPT:
        transcript = os.getenv(AI_ASR_STUB_TRANSCRIPT_ENV, DEFAULT_FIXED_TRANSCRIPT)
        return FixedTranscriptASRProvider(transcript=transcript)

    if stub_mode not in {"", "echo"}:
        raise RuntimeError(
            "Unsupported AI ASR stub mode. "
            f"Expected '', 'echo', or '{AI_ASR_STUB_MODE_FIXED_TRANSCRIPT}', got '{stub_mode}'."
        )

    provider = os.getenv(AI_ASR_PROVIDER_ENV, AI_ASR_PROVIDER_ECHO).strip().lower()
    if provider in {"", AI_ASR_PROVIDER_ECHO}:
        return EchoASRProvider()

    if provider == AI_ASR_PROVIDER_OPENAI:
        api_key = _get_openai_api_key()
        model = os.getenv(AI_ASR_OPENAI_MODEL_ENV, DEFAULT_OPENAI_TRANSCRIPTION_MODEL).strip()
        base_url = os.getenv(AI_ASR_OPENAI_BASE_URL_ENV, "https://api.openai.com/v1").strip()
        timeout_seconds = float(os.getenv(AI_ASR_OPENAI_TIMEOUT_SECONDS_ENV, "20").strip())
        return OpenAIASRProvider(
            transport=OpenAIHTTPTranscriptionTransport(
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            ),
            model=model,
        )

    if provider == AI_ASR_PROVIDER_TENCENT:
        secret_id, secret_key = _get_tencent_credentials()
        default_engine_model_type = os.getenv(
            AI_ASR_TENCENT_ENGINE_MODEL_TYPE_ENV,
            DEFAULT_TENCENT_ENGINE_MODEL_TYPE,
        ).strip()
        region = os.getenv(AI_ASR_TENCENT_REGION_ENV, "ap-shanghai").strip()
        endpoint = os.getenv(AI_ASR_TENCENT_ENDPOINT_ENV, "https://asr.tencentcloudapi.com").strip()
        timeout_seconds = float(os.getenv(AI_ASR_TENCENT_TIMEOUT_SECONDS_ENV, "20").strip())
        return TencentASRProvider(
            transport=TencentCloudSentenceRecognitionHTTPTransport(
                secret_id=secret_id,
                secret_key=secret_key,
                endpoint=endpoint,
                region=region,
                timeout_seconds=timeout_seconds,
            ),
            default_engine_model_type=default_engine_model_type,
        )

    raise RuntimeError(
        "Unsupported AI ASR provider. "
        f"Expected '{AI_ASR_PROVIDER_ECHO}', '{AI_ASR_PROVIDER_OPENAI}', "
        f"or '{AI_ASR_PROVIDER_TENCENT}', got '{provider}'."
    )


def _get_openai_api_key() -> str:
    api_key = os.getenv(AI_ASR_OPENAI_API_KEY_ENV, "").strip() or os.getenv(OPENAI_API_KEY_ENV, "").strip()
    if not api_key:
        raise RuntimeError(
            "OpenAI ASR provider selected but no API key found. "
            f"Set {AI_ASR_OPENAI_API_KEY_ENV} or {OPENAI_API_KEY_ENV}."
        )
    return api_key


def get_llm_provider():
    provider = os.getenv(AI_LLM_PROVIDER_ENV, AI_LLM_PROVIDER_SIMPLE).strip().lower()
    if provider in {"", AI_LLM_PROVIDER_SIMPLE}:
        return SimpleLLMProvider()

    if provider == AI_LLM_PROVIDER_DEEPSEEK:
        api_key = _get_env_with_fallback(
            provider_name="DeepSeek LLM",
            primary_env=AI_LLM_DEEPSEEK_API_KEY_ENV,
            fallback_env=DEEPSEEK_API_KEY_ENV,
        )
        model = os.getenv(AI_LLM_DEEPSEEK_MODEL_ENV, DEFAULT_DEEPSEEK_LLM_MODEL).strip()
        base_url = os.getenv(AI_LLM_DEEPSEEK_BASE_URL_ENV, "https://api.deepseek.com").strip()
        timeout_seconds = float(os.getenv(AI_LLM_DEEPSEEK_TIMEOUT_SECONDS_ENV, "20").strip())
        max_tokens = int(os.getenv(AI_LLM_DEEPSEEK_MAX_TOKENS_ENV, "220").strip())
        temperature = float(os.getenv(AI_LLM_DEEPSEEK_TEMPERATURE_ENV, "0.7").strip())
        return DeepSeekLLMProvider(
            transport=DeepSeekHTTPChatCompletionsTransport(
                api_key=api_key,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            ),
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    raise RuntimeError(
        "Unsupported AI LLM provider. "
        f"Expected '{AI_LLM_PROVIDER_SIMPLE}' or '{AI_LLM_PROVIDER_DEEPSEEK}', got '{provider}'."
    )


def get_tts_provider():
    provider = os.getenv(AI_TTS_PROVIDER_ENV, AI_TTS_PROVIDER_SIMPLE).strip().lower()
    if provider in {"", AI_TTS_PROVIDER_SIMPLE}:
        return SimpleTTSProvider()

    if provider == AI_TTS_PROVIDER_VOLCENGINE:
        appid = _get_env_with_fallback(
            provider_name="Volcengine TTS",
            primary_env=AI_TTS_VOLCENGINE_APPID_ENV,
            fallback_env=VOLCENGINE_TTS_APPID_ENV,
        )
        access_key = _get_env_with_fallback(
            provider_name="Volcengine TTS",
            primary_env=AI_TTS_VOLCENGINE_ACCESS_KEY_ENV,
            fallback_env=VOLCENGINE_TTS_ACCESS_KEY_ENV,
        )
        resource_id = os.getenv(
            AI_TTS_VOLCENGINE_RESOURCE_ID_ENV,
            DEFAULT_VOLCENGINE_TTS_RESOURCE_ID,
        ).strip()
        endpoint = os.getenv(
            AI_TTS_VOLCENGINE_ENDPOINT_ENV,
            "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse",
        ).strip()
        timeout_seconds = float(os.getenv(AI_TTS_VOLCENGINE_TIMEOUT_SECONDS_ENV, "20").strip())
        audio_format = os.getenv(AI_TTS_VOLCENGINE_AUDIO_FORMAT_ENV, "wav").strip().lower()
        sample_rate = int(os.getenv(AI_TTS_VOLCENGINE_SAMPLE_RATE_ENV, "24000").strip())
        default_voice = os.getenv(
            AI_TTS_VOLCENGINE_DEFAULT_VOICE_ENV,
            DEFAULT_VOLCENGINE_TTS_VOICE,
        ).strip()
        default_uid = os.getenv(AI_TTS_VOLCENGINE_UID_ENV, "ai-pet-server").strip()
        model = os.getenv(AI_TTS_VOLCENGINE_MODEL_ENV, "").strip() or None
        return VolcengineTTSProvider(
            transport=VolcengineHTTPSSETTSTransport(
                endpoint=endpoint,
                timeout_seconds=timeout_seconds,
            ),
            appid=appid,
            access_key=access_key,
            resource_id=resource_id,
            audio_format=audio_format,
            sample_rate=sample_rate,
            default_voice_type=default_voice,
            default_uid=default_uid,
            model=model,
            voice_map=DEFAULT_VOLCENGINE_TTS_VOICE_MAP,
        )

    raise RuntimeError(
        "Unsupported AI TTS provider. "
        f"Expected '{AI_TTS_PROVIDER_SIMPLE}' or '{AI_TTS_PROVIDER_VOLCENGINE}', got '{provider}'."
    )


def _get_env_with_fallback(*, provider_name: str, primary_env: str, fallback_env: str) -> str:
    value = os.getenv(primary_env, "").strip() or os.getenv(fallback_env, "").strip()
    if not value:
        raise RuntimeError(
            f"{provider_name} selected but required credentials are missing. "
            f"Set {primary_env} or {fallback_env}."
        )
    return value


def _get_tencent_credentials() -> tuple[str, str]:
    secret_id = os.getenv(AI_ASR_TENCENT_SECRET_ID_ENV, "").strip() or os.getenv(
        TENCENTCLOUD_SECRET_ID_ENV,
        "",
    ).strip()
    secret_key = os.getenv(AI_ASR_TENCENT_SECRET_KEY_ENV, "").strip() or os.getenv(
        TENCENTCLOUD_SECRET_KEY_ENV,
        "",
    ).strip()
    if not secret_id or not secret_key:
        raise RuntimeError(
            "Tencent ASR provider selected but credentials are incomplete. "
            f"Set {AI_ASR_TENCENT_SECRET_ID_ENV}/{AI_ASR_TENCENT_SECRET_KEY_ENV} "
            f"or {TENCENTCLOUD_SECRET_ID_ENV}/{TENCENTCLOUD_SECRET_KEY_ENV}."
        )
    return secret_id, secret_key

def get_voice_loop_orchestrator(db: Session = Depends(get_db)) -> VoiceLoopOrchestrator:
    return VoiceLoopOrchestrator(
        config=OrchestratorConfig(),
        asr=get_asr_provider(),
        persona=StaticPersonaProvider(),
        entitlement=StaticEntitlementProvider(),
        memory=DatabaseMemoryProvider(SqlAlchemyContinuityMemoryRepository(db)),
        safety=RuleBasedSafetyProvider(),
        llm=get_llm_provider(),
        tts=get_tts_provider(),
    )


def get_voice_loop_integration_service(
    service: RepositoryBackedBackendFoundationService = Depends(get_service),
    orchestrator: VoiceLoopOrchestrator = Depends(get_voice_loop_orchestrator),
) -> BackendVoiceLoopIntegrationService:
    return BackendVoiceLoopIntegrationService(
        backend_service=service,
        orchestrator=orchestrator,
    )
