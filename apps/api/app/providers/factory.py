from app.config import Settings
from app.domain.provider import ModelProvider
from app.providers.mock import MockModelProvider


def build_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider == "mock":
        return MockModelProvider()
    from app.providers.deepseek import OpenAIAgentsProvider

    return OpenAIAgentsProvider(settings)
