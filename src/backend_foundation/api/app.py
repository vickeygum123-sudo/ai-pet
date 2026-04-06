"""FastAPI app for the backend foundation MVP scope."""

from __future__ import annotations

import base64
import binascii
import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..application import RepositoryBackedBackendFoundationService
from ..errors import ConflictError, NotFoundError
from ..models import BindStatus, FailureCode, SessionState
from ..persistence.database import Base, create_engine_from_url, get_database_url
from ..voice_loop_integration import BackendVoiceLoopIntegrationService, RunVoiceLoopCommand
from .dependencies import (
    get_current_account_id,
    get_db,
    get_service,
    get_voice_loop_integration_service,
)
from .errors import ACCOUNT_CONFLICT, DEVICE_CONFLICT, api_error
from .runtime_audio_store import VoiceLoopAudioStore
from .schemas import (
    AccountResponse,
    AdminOverviewResponse,
    BindDeviceRequest,
    BindingResponse,
    CreateAccountRequest,
    DeviceListResponse,
    DeviceResponse,
    EntitlementSnapshotResponse,
    ErrorResponse,
    RegisterDeviceRequest,
    RunVoiceLoopRequest,
    SessionListResponse,
    SessionResponse,
    StartSessionRequest,
    UpdateSessionRequest,
    VoiceLoopExecutionResponse,
)

VOICE_LOOP_INCLUDE_AUDIO_ENV = "AI_VOICE_LOOP_INCLUDE_AUDIO"
VOICE_LOOP_AUDIO_MODE_ENV = "AI_VOICE_LOOP_AUDIO_MODE"
VOICE_LOOP_AUDIO_MODE_INLINE = "inline"
VOICE_LOOP_AUDIO_MODE_URL = "url"
VOICE_LOOP_AUDIO_MODE_NONE = "none"


def _get_voice_loop_audio_mode() -> str:
    configured = os.getenv(VOICE_LOOP_AUDIO_MODE_ENV, "").strip().lower()
    if configured in {
        VOICE_LOOP_AUDIO_MODE_INLINE,
        VOICE_LOOP_AUDIO_MODE_URL,
        VOICE_LOOP_AUDIO_MODE_NONE,
    }:
        return configured
    return (
        VOICE_LOOP_AUDIO_MODE_INLINE
        if os.getenv(VOICE_LOOP_INCLUDE_AUDIO_ENV, "1").strip().lower() not in {"0", "false", "no"}
        else VOICE_LOOP_AUDIO_MODE_NONE
    )


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database_url = get_database_url()
        if database_url.startswith("sqlite"):
            engine = create_engine_from_url(database_url)
            Base.metadata.create_all(bind=engine)
        yield

    app = FastAPI(
        title="AI Pet MVP Backend Foundation API",
        version="0.1.0",
        description="Backend MVP foundation for account, device, bind, session, entitlement, and admin query APIs.",
        lifespan=lifespan,
    )
    app.state.voice_loop_audio_store = VoiceLoopAudioStore()

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(code="NOT_FOUND", message=str(exc)).model_dump(by_alias=True),
        )

    @app.exception_handler(ConflictError)
    async def handle_conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(code="CONFLICT", message=str(exc)).model_dump(by_alias=True),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            payload = ErrorResponse(code=str(detail["code"]), message=str(detail["message"]))
        else:
            payload = ErrorResponse(code="HTTP_ERROR", message=str(detail))
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            code="VALIDATION_ERROR",
            message=f"Request validation failed: {exc.errors()[0]['msg']}" if exc.errors() else "Request validation failed.",
        )
        return JSONResponse(status_code=422, content=payload.model_dump(by_alias=True))

    @app.post("/v1/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
    def create_account(
        payload: CreateAccountRequest,
        db: Session = Depends(get_db),
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> AccountResponse:
        try:
            account = service.create_account(
                auth_subject=payload.auth_subject,
                display_name=payload.display_name,
                default_role_id=payload.default_role_id,
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ACCOUNT_CONFLICT from exc
        return AccountResponse.model_validate(account)

    @app.get("/v1/accounts/me", response_model=AccountResponse)
    def get_me(
        account_id: Annotated[str, Depends(get_current_account_id)],
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> AccountResponse:
        return AccountResponse.model_validate(service.get_account(account_id))

    @app.post("/v1/internal/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
    def register_device(
        payload: RegisterDeviceRequest,
        db: Session = Depends(get_db),
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> DeviceResponse:
        try:
            device = service.register_device(
                device_id=payload.device_id,
                hardware_model=payload.hardware_model,
                firmware_version=payload.firmware_version,
                pairing_code=payload.pairing_code,
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise DEVICE_CONFLICT from exc
        return DeviceResponse.model_validate(device)

    @app.post("/v1/device-bindings", response_model=BindingResponse, status_code=status.HTTP_201_CREATED)
    def bind_device(
        payload: BindDeviceRequest,
        account_id: Annotated[str, Depends(get_current_account_id)],
        db: Session = Depends(get_db),
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> BindingResponse:
        try:
            binding = service.bind_device(account_id=account_id, pairing_code=payload.pairing_code)
            db.commit()
        except NotFoundError as exc:
            db.rollback()
            raise api_error(status.HTTP_409_CONFLICT, "BIND_TARGET_UNAVAILABLE", str(exc)) from exc
        return BindingResponse.model_validate(binding)

    @app.delete("/v1/device-bindings/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
    def unbind_device(
        device_id: str,
        account_id: Annotated[str, Depends(get_current_account_id)],
        db: Session = Depends(get_db),
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> Response:
        service.unbind_device(account_id=account_id, device_id=device_id)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/v1/entitlements/me", response_model=EntitlementSnapshotResponse)
    def get_entitlement(
        account_id: Annotated[str, Depends(get_current_account_id)],
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> EntitlementSnapshotResponse:
        return EntitlementSnapshotResponse.model_validate(service.get_entitlement(account_id))

    @app.post("/v1/device-sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
    def start_session(
        payload: StartSessionRequest,
        db: Session = Depends(get_db),
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> SessionResponse:
        session = service.start_session(
            account_id=payload.account_id,
            device_id=payload.device_id,
            firmware_version=payload.firmware_version,
            role_id=payload.role_id,
        )
        db.commit()
        return SessionResponse.model_validate(session)

    @app.patch("/v1/device-sessions/{session_id}", response_model=SessionResponse)
    def update_session(
        session_id: str,
        payload: UpdateSessionRequest,
        db: Session = Depends(get_db),
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> SessionResponse:
        update_kwargs: dict[str, object] = {
            "asr_status": payload.asr_status,
            "llm_status": payload.llm_status,
            "tts_status": payload.tts_status,
            "safety_flag": payload.safety_flag,
            "fallback_used": payload.fallback_used,
            "continuity_recall_used": payload.continuity_recall_used,
            "first_response_latency_ms": payload.first_response_latency_ms,
            "notes": payload.notes,
        }
        if "failure_code" in payload.model_fields_set:
            update_kwargs["failure_code"] = payload.failure_code

        session = service.update_session(
            session_id=session_id,
            state=payload.state,
            **update_kwargs,
        )
        db.commit()
        return SessionResponse.model_validate(session)

    @app.post(
        "/v1/internal/device-sessions/{session_id}/voice-loop",
        response_model=VoiceLoopExecutionResponse,
    )
    def run_voice_loop(
        request: Request,
        session_id: str,
        payload: RunVoiceLoopRequest,
        db: Session = Depends(get_db),
        integration: BackendVoiceLoopIntegrationService = Depends(get_voice_loop_integration_service),
    ) -> VoiceLoopExecutionResponse:
        try:
            audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
        except binascii.Error as exc:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "INVALID_AUDIO_PAYLOAD",
                "audioBase64 must be valid base64.",
            ) from exc

        result = integration.run(
            session_id=session_id,
            command=RunVoiceLoopCommand(
                request_id=payload.request_id,
                audio_bytes=audio_bytes,
                audio_format=payload.audio_format,
                sample_rate_hz=payload.sample_rate_hz,
                duration_ms=payload.duration_ms,
                locale=payload.locale,
            ),
        )
        db.commit()
        audio_mode = _get_voice_loop_audio_mode()
        audio_url: str | None = None
        if (
            audio_mode == VOICE_LOOP_AUDIO_MODE_URL
            and result.ai_response.audio_bytes is not None
            and result.ai_response.audio_format is not None
        ):
            request.app.state.voice_loop_audio_store.put(
                session_id=session_id,
                request_id=payload.request_id,
                audio_bytes=result.ai_response.audio_bytes,
                audio_format=result.ai_response.audio_format,
            )
            audio_url = str(
                request.url_for(
                    "get_voice_loop_audio",
                    session_id=session_id,
                    request_id=payload.request_id,
                )
            )
        return VoiceLoopExecutionResponse(
            session=SessionResponse.model_validate(result.session),
            transcript=result.ai_response.transcript,
            response_text=result.ai_response.response_text,
            audio_base64=(
                base64.b64encode(result.ai_response.audio_bytes).decode("ascii")
                if audio_mode == VOICE_LOOP_AUDIO_MODE_INLINE and result.ai_response.audio_bytes is not None
                else None
            ),
            audio_format=result.ai_response.audio_format if audio_mode != VOICE_LOOP_AUDIO_MODE_NONE else None,
            audio_url=audio_url,
            fallback_mode=result.ai_response.fallback_mode.value,
            runtime_failure_code=result.ai_response.failure_code.value,
            safety_tags=list(result.ai_response.safety_tags),
            recalled_memories=list(result.ai_response.recalled_memories),
            warnings=list(result.ai_response.warnings),
        )

    @app.get("/v1/internal/device-sessions/{session_id}/voice-loop-audio/{request_id}", name="get_voice_loop_audio")
    def get_voice_loop_audio(request: Request, session_id: str, request_id: str) -> Response:
        artifact = request.app.state.voice_loop_audio_store.get(
            session_id=session_id,
            request_id=request_id,
        )
        if artifact is None:
            raise api_error(
                status.HTTP_404_NOT_FOUND,
                "VOICE_LOOP_AUDIO_NOT_FOUND",
                "Voice-loop audio artifact was not found for the requested turn.",
            )
        return Response(
            content=artifact.audio_bytes,
            media_type=artifact.audio_format,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/v1/admin/overview", response_model=AdminOverviewResponse)
    def get_admin_overview(
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> AdminOverviewResponse:
        return AdminOverviewResponse.model_validate(service.get_admin_overview())

    @app.get("/v1/admin/devices", response_model=DeviceListResponse)
    def list_admin_devices(
        bind_status: Annotated[BindStatus | None, Query()] = None,
        owner_account_id: Annotated[str | None, Query()] = None,
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> DeviceListResponse:
        items = service.list_admin_devices(bind_status=bind_status, owner_account_id=owner_account_id)
        return DeviceListResponse(items=[DeviceResponse.model_validate(item) for item in items])

    @app.get("/v1/admin/sessions", response_model=SessionListResponse)
    def list_admin_sessions(
        state: Annotated[SessionState | None, Query()] = None,
        failure_code: Annotated[FailureCode | None, Query()] = None,
        account_id: Annotated[str | None, Query()] = None,
        device_id: Annotated[str | None, Query()] = None,
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> SessionListResponse:
        items = service.list_admin_sessions(
            state=state,
            failure_code=failure_code,
            account_id=account_id,
            device_id=device_id,
        )
        return SessionListResponse(items=[SessionResponse.model_validate(item) for item in items])

    @app.get("/v1/admin/sessions/{session_id}", response_model=SessionResponse)
    def get_admin_session_detail(
        session_id: str,
        service: RepositoryBackedBackendFoundationService = Depends(get_service),
    ) -> SessionResponse:
        return SessionResponse.model_validate(service.get_admin_session_detail(session_id))

    return app
