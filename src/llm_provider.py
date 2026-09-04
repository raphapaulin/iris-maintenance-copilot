"""Minimal vendor-neutral LLM interface and OpenAI-compatible HTTP provider."""

import json
import os
import re
import time
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RETRYABLE_HTTP_STATUSES = {429, 500, 502, 503, 504}
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_INITIAL_RETRY_DELAY = 2.0
MAX_ERROR_DETAIL_LENGTH = 300


class LLMProvider(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


class LLMProviderError(RuntimeError):
    """Raised when LLM configuration or generation fails."""


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url,
        api_key,
        model,
        timeout=60,
        max_attempts=DEFAULT_MAX_ATTEMPTS,
        initial_retry_delay=DEFAULT_INITIAL_RETRY_DELAY,
        opener=None,
        sleep_func=None,
        retry_notifier=None,
    ):
        if not base_url:
            raise LLMProviderError("LLM_BASE_URL environment variable is required")
        if not api_key:
            raise LLMProviderError("LLM_API_KEY environment variable is required")
        if not model:
            raise LLMProviderError("LLM_MODEL environment variable is required")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be a positive integer")
        if initial_retry_delay < 0:
            raise ValueError("initial_retry_delay must not be negative")
        self.endpoint = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.initial_retry_delay = initial_retry_delay
        self.opener = opener or urlopen
        self.sleep_func = sleep_func or time.sleep
        self.retry_notifier = retry_notifier or print

    @classmethod
    def from_environment(cls):
        return cls(
            base_url=os.getenv("LLM_BASE_URL"),
            api_key=os.getenv("LLM_API_KEY"),
            model=os.getenv("LLM_MODEL"),
        )

    def _safe_error_detail(self, error):
        try:
            raw_body = error.read(MAX_ERROR_DETAIL_LENGTH * 4).decode(
                "utf-8", errors="replace"
            )
        except Exception:
            return "provider returned no readable error details"

        detail = raw_body
        try:
            error_data = json.loads(raw_body)
            if isinstance(error_data, dict):
                provider_error = error_data.get("error", error_data)
                if isinstance(provider_error, dict):
                    detail = provider_error.get("message", raw_body)
        except json.JSONDecodeError:
            pass

        detail = " ".join(str(detail).split())
        if self.api_key:
            detail = detail.replace(self.api_key, "[REDACTED]")
        detail = re.sub(
            r"(?i)authorization\s*[:=]\s*bearer\s+\S+",
            "authorization=[REDACTED]",
            detail,
        )
        if not detail:
            return "provider returned an empty error body"
        return detail[:MAX_ERROR_DETAIL_LENGTH]

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
        ).encode("utf-8")
        request = Request(
            self.endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        for attempt in range(1, self.max_attempts + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    response_data = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as error:
                detail = self._safe_error_detail(error)
                if error.code in RETRYABLE_HTTP_STATUSES and attempt < self.max_attempts:
                    delay = self.initial_retry_delay * (2 ** (attempt - 1))
                    self.retry_notifier(
                        f"LLM request returned HTTP {error.code}; retrying in "
                        f"{delay:g}s (attempt {attempt}/{self.max_attempts})."
                    )
                    self.sleep_func(delay)
                    continue
                raise LLMProviderError(
                    f"LLM request failed with HTTP {error.code} after "
                    f"{attempt} attempt(s): {detail}"
                ) from error
            except URLError as error:
                raise LLMProviderError(f"LLM request failed: {error.reason}") from error
            except json.JSONDecodeError as error:
                raise LLMProviderError("LLM provider returned invalid response JSON") from error

        try:
            content = response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LLMProviderError("LLM response did not contain message content") from error
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("LLM response content was empty")
        return content
