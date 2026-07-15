import json
from collections.abc import Mapping

from pydantic import ValidationError

from app.prompt.models import WorkAssistantResponse


class InvalidModelOutput(ValueError):
    pass


class OutputValidator:
    def validate(self, value: str | Mapping[str, object]) -> WorkAssistantResponse:
        try:
            payload = json.loads(value) if isinstance(value, str) else dict(value)
            response = WorkAssistantResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise InvalidModelOutput("model output does not match schema") from error

        if response.mode == "answer" and not (response.conclusion and response.next_steps):
            raise InvalidModelOutput("answer requires conclusion and next_steps")
        if response.mode == "clarification" and not response.open_questions:
            raise InvalidModelOutput("clarification requires open_questions")
        if response.mode == "refusal" and not response.notice:
            raise InvalidModelOutput("refusal requires notice")
        return response
