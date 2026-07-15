import asyncio
import json
from collections.abc import AsyncIterator, Iterator

from app.domain.provider import ModelEvent, ModelRequest
from app.prompt.models import WorkAssistantResponse


def chunk_text(value: str, size: int) -> Iterator[str]:
    for offset in range(0, len(value), size):
        yield value[offset : offset + size]


def choose_response(user_input: str) -> WorkAssistantResponse:
    lowered = user_input.lower()
    if "api key" in lowered or "系统提示词" in user_input or "忽略规则" in user_input:
        return WorkAssistantResponse(
            mode="refusal",
            notice="无法提供系统配置或敏感凭据，但可以继续协助梳理工作事项。",
        )
    if user_input.strip() == "帮我处理一下":
        return WorkAssistantResponse(
            mode="clarification",
            open_questions=["你希望处理哪项工作，以及期望得到什么结果？"],
            notice="需要补充必要信息后才能继续。",
        )
    return WorkAssistantResponse(
        mode="answer",
        conclusion="当前发布存在需要在上线前确认的风险。",
        risks=["接口兼容性尚未确认", "回滚演练结果未知", "监控阈值尚未复核"],
        open_questions=["各风险项的负责人和确认期限是什么？"],
        next_steps=["确认负责人", "完成回滚演练", "复核监控与告警阈值"],
    )


class MockModelProvider:
    name = "mock"

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        user_input = request.prompt.messages[-1].content
        if "[mock:error]" in user_input:
            yield ModelEvent.error(
                "MODEL_UNAVAILABLE",
                "模拟模型暂时不可用。",
                retryable=True,
            )
            return

        encoded = (
            "{not-json"
            if "[mock:invalid]" in user_input
            else json.dumps(
                choose_response(user_input).model_dump(),
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        for sequence, chunk in enumerate(chunk_text(encoded, 24), start=1):
            if request.cancel.cancelled:
                yield ModelEvent.cancelled()
                return
            yield ModelEvent.delta_event(sequence, chunk)
            await asyncio.sleep(0)
        yield ModelEvent.completed()
