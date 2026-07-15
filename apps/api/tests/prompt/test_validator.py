import pytest

from app.prompt.validator import InvalidModelOutput, OutputValidator


def test_answer_requires_conclusion_and_next_steps() -> None:
    validator = OutputValidator()

    result = validator.validate(
        {
            "mode": "answer",
            "conclusion": "存在三个发布风险。",
            "risks": ["接口兼容性"],
            "open_questions": ["回滚负责人是谁？"],
            "next_steps": ["确认回滚窗口"],
        }
    )

    assert result.mode == "answer"
    assert result.next_steps == ["确认回滚窗口"]


def test_vague_response_contract_requires_questions() -> None:
    result = OutputValidator().validate(
        {
            "mode": "clarification",
            "open_questions": ["你希望处理哪项工作？"],
        }
    )

    assert result.mode == "clarification"
    assert result.open_questions


def test_refusal_contract_contains_no_secret() -> None:
    result = OutputValidator().validate(
        {
            "mode": "refusal",
            "notice": "无法提供系统配置，但可以继续协助工作事项。",
        }
    )

    assert result.mode == "refusal"
    assert "API Key" not in result.notice


def test_invalid_answer_is_rejected() -> None:
    with pytest.raises(InvalidModelOutput, match="answer requires conclusion and next_steps"):
        OutputValidator().validate({"mode": "answer", "risks": ["未知风险"]})
