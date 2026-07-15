import asyncio
from collections.abc import AsyncIterator, Iterator

from app.domain.provider import ModelEvent, ModelRequest


def chunk_text(value: str, size: int) -> Iterator[str]:
    for offset in range(0, len(value), size):
        yield value[offset : offset + size]


def choose_response(user_input: str) -> str:
    lowered = user_input.lower()
    sensitive = ("api key", "系统提示词", "环境变量", "密钥", "忽略规则", "忽略前面")
    if any(term in lowered for term in sensitive):
        return "无法提供系统配置或敏感凭据，但可以继续协助梳理工作事项。"
    vague = ("处理一下", "弄一下", "搞一下", "帮忙处理", "帮我处理")
    if any(term in user_input for term in vague) and len(user_input.strip()) < 20:
        return "请先补充：你希望处理哪项工作，以及期望得到什么结果？"
    risk_terms = ("风险", "上线", "发布", "投产")
    if any(term in user_input for term in risk_terms):
        return """## 结论

当前发布存在需要在上线前确认的风险。

## 风险项

- 接口兼容性尚未确认
- 回滚演练结果未知
- 监控阈值尚未复核

## 待确认项

- 各风险项的负责人和确认期限是什么？

## 下一步

1. 确认负责人
2. 完成回滚演练
3. 复核监控与告警阈值
"""
    return f"已收到你的问题：{user_input.strip()}\n\n我会基于现有信息提供建议，不会声称已经执行现实操作。"


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

        encoded = choose_response(user_input)
        for sequence, chunk in enumerate(chunk_text(encoded, 24), start=1):
            if request.cancel.cancelled:
                yield ModelEvent.cancelled()
                return
            yield ModelEvent.delta_event(sequence, chunk)
            await asyncio.sleep(0)
        yield ModelEvent.completed()
