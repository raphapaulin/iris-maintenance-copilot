"""Controlled validation for bounded LLM HTTP retry behavior."""

import io
import json
from urllib.error import HTTPError

from src.llm_provider import LLMProviderError, OpenAICompatibleProvider


SUCCESS_BODY = json.dumps(
    {"choices": [{"message": {"content": '{"ok":true}'}}]}
).encode("utf-8")


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return self.body


class SequenceOpener:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = 0

    def __call__(self, request, timeout):
        self.calls += 1
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def http_error(status, message):
    body = json.dumps({"error": {"message": message}}).encode("utf-8")
    return HTTPError(
        url="https://provider.invalid/chat/completions",
        code=status,
        msg="controlled error",
        hdrs=None,
        fp=io.BytesIO(body),
    )


def provider_for(outcomes, api_key="controlled-secret"):
    opener = SequenceOpener(outcomes)
    delays = []
    notices = []
    provider = OpenAICompatibleProvider(
        base_url="https://provider.invalid/v1",
        api_key=api_key,
        model="controlled-model",
        max_attempts=3,
        initial_retry_delay=2,
        opener=opener,
        sleep_func=delays.append,
        retry_notifier=notices.append,
    )
    return provider, opener, delays, notices


def validate_retry_then_success():
    provider, opener, delays, notices = provider_for(
        [http_error(503, "temporarily unavailable"), FakeResponse(SUCCESS_BODY)]
    )
    assert provider.generate("system", "user") == '{"ok":true}'
    assert opener.calls == 2
    assert delays == [2]
    assert notices == [
        "LLM request returned HTTP 503; retrying in 2s (attempt 1/3)."
    ]


def validate_repeated_transient_failure():
    provider, opener, delays, notices = provider_for(
        [
            http_error(503, "overloaded one"),
            http_error(503, "overloaded two"),
            http_error(503, "overloaded three"),
        ]
    )
    try:
        provider.generate("system", "user")
    except LLMProviderError as error:
        message = str(error)
        assert "HTTP 503" in message
        assert "after 3 attempt(s)" in message
        assert "overloaded three" in message
    else:
        raise AssertionError("Repeated HTTP 503 did not fail")
    assert opener.calls == 3
    assert delays == [2, 4]
    assert len(notices) == 2


def validate_non_retryable_failure():
    provider, opener, delays, notices = provider_for(
        [http_error(400, "invalid request")]
    )
    try:
        provider.generate("system", "user")
    except LLMProviderError as error:
        assert "HTTP 400" in str(error)
        assert "after 1 attempt(s)" in str(error)
    else:
        raise AssertionError("HTTP 400 did not fail")
    assert opener.calls == 1
    assert delays == []
    assert notices == []


def validate_secret_redaction():
    secret = "controlled-secret-value"
    provider, _, _, _ = provider_for(
        [
            http_error(503, f"Authorization: Bearer {secret}"),
            http_error(503, f"request contained {secret}"),
            http_error(503, f"request contained {secret}"),
        ],
        api_key=secret,
    )
    try:
        provider.generate("system", "user")
    except LLMProviderError as error:
        assert secret not in str(error)
        assert "Bearer" not in str(error)
    else:
        raise AssertionError("Controlled secret-redaction failure did not occur")


def main():
    validate_retry_then_success()
    print("503 followed by success: PASSED")
    validate_repeated_transient_failure()
    print("Repeated 503 bounded failure: PASSED")
    validate_non_retryable_failure()
    print("HTTP 400 immediate failure: PASSED")
    validate_secret_redaction()
    print("Credential redaction: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
