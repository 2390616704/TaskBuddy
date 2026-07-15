from dataclasses import asdict, dataclass

from app.config import Settings
from app.domain.provider import ModelProvider
from app.providers.mock import MockModelProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


class ProviderNotFoundError(LookupError):
    pass


class ProviderUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    id: str
    display_name: str
    model_name: str
    available: bool

    def public_dict(self) -> dict[str, str | bool]:
        data = asdict(self)
        return {
            "id": str(data["id"]),
            "displayName": str(data["display_name"]),
            "modelName": str(data["model_name"]),
            "available": bool(data["available"]),
        }


class ProviderRegistry:
    def __init__(self, settings: Settings, override: ModelProvider | None = None) -> None:
        mock = override or MockModelProvider()
        self._providers: dict[str, ModelProvider] = {mock.name: mock}
        self._metadata = {
            mock.name: ProviderInfo(mock.name, "Mock", "deterministic", True),
            "openai-compatible": ProviderInfo(
                "openai-compatible",
                settings.model_display_name,
                settings.model_name,
                settings.model_api_key is not None,
            ),
        }
        if settings.model_api_key is not None and override is None:
            self._providers["openai-compatible"] = OpenAICompatibleProvider(settings)

    def list_public(self) -> list[dict[str, str | bool]]:
        return [info.public_dict() for info in self._metadata.values()]

    def require_available(self, provider_id: str) -> ModelProvider:
        if provider_id not in self._metadata:
            raise ProviderNotFoundError(provider_id)
        provider = self._providers.get(provider_id)
        if provider is None:
            raise ProviderUnavailableError(provider_id)
        return provider
