import asyncio
from collections.abc import AsyncIterator

from pydantic import SecretStr

from app.config import Settings
from app.domain.provider import CancelSignal, ModelRequest
from app.prompt.builder import PromptBuilder
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.registry import ProviderRegistry, ProviderUnavailableError


async def fake_stream(_: str, __: list[dict[str, str]]) -> AsyncIterator[str]:
    yield "第一段"
    yield "第二段"


async def blocked_stream(_: str, __: list[dict[str, str]]) -> AsyncIterator[str]:
    await asyncio.Event().wait()
    yield "永远不会到达"


def model_request() -> ModelRequest:
    return ModelRequest(
        prompt=PromptBuilder(system_text="系统规则").build([], "分析风险"),
        cancel=CancelSignal(),
    )


def test_registry_exposes_unconfigured_real_provider_without_secret() -> None:
    registry = ProviderRegistry(Settings(model_api_key=None))

    providers = registry.list_public()

    assert providers[0]["id"] == "mock"
    assert providers[1]["id"] == "openai-compatible"
    assert providers[1]["available"] is False
    assert "apiKey" not in providers[1]


def test_registry_rejects_unconfigured_real_provider() -> None:
    registry = ProviderRegistry(Settings(model_api_key=None))

    try:
        registry.require_available("openai-compatible")
    except ProviderUnavailableError:
        pass
    else:
        raise AssertionError("unconfigured provider must be unavailable")


def test_provider_uses_configured_base_url_and_model() -> None:
    provider = OpenAICompatibleProvider(
        Settings(
            model_api_key=SecretStr("test-secret-value"),
            model_base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
        ),
        stream_factory=fake_stream,
    )

    assert str(provider.client.base_url).rstrip("/") == "https://api.deepseek.com"
    assert provider.model_name == "deepseek-v4-flash"
    assert "test-secret-value" not in repr(provider)


async def test_provider_maps_text_stream_to_internal_events() -> None:
    provider = OpenAICompatibleProvider(
        Settings(model_api_key=SecretStr("test-secret-value")),
        stream_factory=fake_stream,
    )

    events = [event async for event in provider.stream(model_request())]

    assert [event.type for event in events] == ["delta", "delta", "completed"]
    assert [event.sequence for event in events[:-1]] == [1, 2]
    assert [event.delta for event in events[:-1]] == ["第一段", "第二段"]


async def test_cancel_interrupts_a_stalled_upstream() -> None:
    provider = OpenAICompatibleProvider(
        Settings(model_api_key=SecretStr("test-secret-value")),
        stream_factory=blocked_stream,
    )
    request = model_request()
    stream = provider.stream(request)
    pending = asyncio.create_task(anext(stream))

    await asyncio.sleep(0)
    request.cancel.cancel()
    event = await asyncio.wait_for(pending, timeout=0.5)

    assert event.type == "cancelled"
