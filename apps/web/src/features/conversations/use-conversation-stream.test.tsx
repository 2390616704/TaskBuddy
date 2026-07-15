import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "./api";
import { useConversationStream } from "./use-conversation-stream";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return { ...actual, sendMessage: vi.fn(), cancelMessage: vi.fn() };
});

describe("useConversationStream", () => {
  beforeEach(() => vi.clearAllMocks());

  it("reduces stream events and reconciles after a terminal event", async () => {
    const onSettled = vi.fn(async () => undefined);
    vi.mocked(api.sendMessage).mockImplementation(async (_request, onEvent) => {
      onEvent({
        name: "message.accepted",
        data: { requestId: "r1", userMessageId: "u1", messageId: "m1" },
      });
      onEvent({
        name: "message.delta",
        data: { messageId: "m1", sequence: 1, delta: "风险" },
      });
      onEvent({
        name: "message.completed",
        data: {
          messageId: "m1",
          status: "completed",
          content: {
            mode: "answer",
            conclusion: "存在风险",
            risks: [],
            open_questions: [],
            next_steps: ["确认"],
            notice: "",
          },
        },
      });
    });
    const { result } = renderHook(() => useConversationStream({ onSettled }));

    await act(() => result.current.send("c1", "分析风险"));

    expect(result.current.state.status).toBe("completed");
    expect(result.current.state.content?.conclusion).toBe("存在风险");
    expect(onSettled).toHaveBeenCalledWith("c1");
  });
});
