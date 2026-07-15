import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Message } from "@/features/conversations/types";

import { MessageCard } from "./message-card";

const completedRiskMessage: Message = {
  id: "m1",
  conversationId: "c1",
  role: "assistant",
  status: "completed",
  content: {
    mode: "answer",
    conclusion: "存在三个发布风险。",
    risks: ["接口兼容性"],
    open_questions: ["负责人是谁？"],
    next_steps: ["确认回滚窗口"],
    notice: "",
  },
  inReplyToMessageId: "u1",
  retryOfMessageId: null,
  errorCode: null,
  createdAt: "2026-07-15T12:00:00Z",
  updatedAt: "2026-07-15T12:00:01Z",
};

describe("MessageCard", () => {
  it("renders structured fields instead of provider JSON", () => {
    render(<MessageCard message={completedRiskMessage} />);

    expect(screen.getByRole("heading", { name: "结论" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "风险项" })).toBeVisible();
    expect(screen.getByText("接口兼容性")).toBeVisible();
    expect(screen.queryByText(/\{"mode"/)).not.toBeInTheDocument();
  });

  it("offers retry for a failed assistant message", async () => {
    const retry = vi.fn();
    render(
      <MessageCard
        message={{
          ...completedRiskMessage,
          content: "",
          status: "failed",
          errorCode: "MODEL_UNAVAILABLE",
        }}
        onRetry={retry}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "重试" }));

    expect(retry).toHaveBeenCalledWith("m1");
    expect(screen.getByText("生成失败")).toBeVisible();
  });
});
