from __future__ import annotations

import json
from typing import Any, Protocol
from urllib import error, request

from .contracts import ProviderError
from .providers import LLMResultEnvelope, PromptContext


class DeepSeekChatCompletionsTransport(Protocol):
    def generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        ...


class DeepSeekHTTPChatCompletionsTransport:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def generate(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "n": 1,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        http_request = request.Request(
            url=f"{self._base_url}/chat/completions",
            data=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(
                f"deepseek chat request failed with status {exc.code}: {detail[:200]}"
            ) from exc
        except error.URLError as exc:
            raise ProviderError("deepseek chat request failed") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError("deepseek chat returned invalid JSON") from exc


class DeepSeekLLMProvider:
    def __init__(
        self,
        *,
        transport: DeepSeekChatCompletionsTransport,
        model: str = "deepseek-chat",
        provider_name: str = "deepseek",
        temperature: float = 0.7,
        max_tokens: int | None = 220,
    ) -> None:
        self._transport = transport
        self._model = model
        self._provider_name = provider_name
        self._temperature = temperature
        self._max_tokens = max_tokens

    def generate(self, prompt: str, context: PromptContext) -> LLMResultEnvelope:
        _ = context
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            raise ProviderError("empty prompt")

        response = self._transport.generate(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only the final spoken assistant reply. "
                        "Keep it concise, natural, and safe for voice playback."
                    ),
                },
                {"role": "user", "content": cleaned_prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        text = extract_message_text(response)
        if not text:
            raise ProviderError("deepseek chat returned empty text")

        usage = response.get("usage")
        model = str(response.get("model", self._model)).strip() or self._model
        return LLMResultEnvelope(
            text=text,
            model=model,
            prompt_tokens=_read_usage_int(usage, "prompt_tokens"),
            completion_tokens=_read_usage_int(usage, "completion_tokens"),
        )


def extract_message_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip()

    return ""


def _read_usage_int(usage: object, field_name: str) -> int:
    if not isinstance(usage, dict):
        return 0

    raw_value = usage.get(field_name, 0)
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, float):
        return int(raw_value)
    if isinstance(raw_value, str):
        try:
            return int(raw_value)
        except ValueError:
            return 0
    return 0
