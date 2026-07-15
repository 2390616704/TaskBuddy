from pathlib import Path

from app.prompt.models import PromptMessage, PromptPackage, WorkAssistantResponse


class PromptBuilder:
    def __init__(
        self,
        system_text: str | None = None,
        history_character_budget: int = 6_000,
    ) -> None:
        system_path = Path(__file__).with_name("system.md")
        self._system_text = system_text or system_path.read_text(encoding="utf-8").strip()
        self._history_character_budget = history_character_budget

    def build(self, history: list[PromptMessage], user_input: str) -> PromptPackage:
        selected: list[PromptMessage] = []
        used_characters = 0
        for message in reversed(history):
            message_length = len(message.content)
            if used_characters + message_length > self._history_character_budget:
                break
            selected.append(message)
            used_characters += message_length
        selected.reverse()

        return PromptPackage(
            messages=[
                PromptMessage(role="system", content=self._system_text),
                *selected,
                PromptMessage(role="user", content=user_input),
            ],
            prompt_version="work-assistant-v1",
            output_schema=WorkAssistantResponse.model_json_schema(),
        )
