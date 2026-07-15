from collections.abc import AsyncIterator

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.domain.provider import CancelSignal, ModelRequest
from app.prompt.builder import PromptBuilder
from app.providers.deepseek import OpenAIAgentsProvider
from app.providers.factory import build_provider


async def fake_stream(_: object, __: list[dict[str, str]]) -> AsyncIterator[str]:
    yield "第一段"
    yield "第二段"


def model_request() -> ModelRequest:
    return ModelRequest(
        prompt=PromptBuilder(system_text="系统规则").build([], "分析风险"),
        cancel=CancelSignal(),
    )


def test_mock_mode_does_not_require_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_CODE_API_KEY", raising=False)

    provider = build_provider(Settings(model_provider="mock"))

    assert provider.name == "mock"


def test_deepseek_mode_requires_server_secret() -> None:
    with pytest.raises(ValidationError, match="DEEPSEEK_CODE_API_KEY"):
        Settings(model_provider="deepseek", deepseek_code_api_key=None)


def test_deepseek_api_key_is_supported_as_compatibility_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_CODE_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "compatibility-secret")

    settings = Settings(model_provider="deepseek")

    assert settings.deepseek_code_api_key is not None
    assert settings.deepseek_code_api_key.get_secret_value() == "compatibility-secret"


def test_deepseek_uses_configured_base_url_without_completion_suffix() -> None:
    provider = OpenAIAgentsProvider(
        Settings(
            model_provider="deepseek",
            deepseek_code_api_key=SecretStr("test-secret-value"),
            deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-v4-flash",
        ),
        stream_factory=fake_stream,
    )

    assert str(provider.client.base_url).rstrip("/") == "https://api.deepseek.com"
    assert provider.model_name == "deepseek-v4-flash"
    assert "test-secret-value" not in repr(provider.settings)


async def test_deepseek_maps_text_stream_to_internal_events() -> None:
    provider = OpenAIAgentsProvider(
        Settings(
            model_provider="deepseek",
            deepseek_code_api_key=SecretStr("test-secret-value"),
        ),
        stream_factory=fake_stream,
    )

    events = [event async for event in provider.stream(model_request())]

    assert [event.type for event in events] == ["delta", "delta", "completed"]
    assert [event.sequence for event in events[:-1]] == [1, 2]
    assert [event.delta for event in events[:-1]] == ["第一段", "第二段"]
