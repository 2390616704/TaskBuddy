import { describe, expect, it } from "vitest";

import { initialStreamState, reduceStreamEvent } from "./stream-state";
import type { StreamEvent } from "./types";

const delta = (sequence: number, value: string): StreamEvent => ({
  name: "message.delta",
  data: { messageId: "m1", sequence, delta: value },
});

describe("reduceStreamEvent", () => {
  it("ignores repeated and older delta sequences", () => {
    const accepted = reduceStreamEvent(initialStreamState, {
      name: "message.accepted",
      data: { requestId: "r1", userMessageId: "u1", messageId: "m1" },
    });
    const first = reduceStreamEvent(accepted, delta(1, "风"));

    expect(reduceStreamEvent(first, delta(1, "风"))).toEqual(first);
    expect(reduceStreamEvent(first, delta(0, "旧"))).toEqual(first);
    expect(reduceStreamEvent(first, delta(2, "险")).text).toBe("风险");
  });

  it("records completed structured content as the terminal state", () => {
    const state = reduceStreamEvent(initialStreamState, {
      name: "message.completed",
      data: {
        messageId: "m1",
        status: "completed",
        content: {
          mode: "answer",
          conclusion: "存在风险",
          risks: ["兼容性"],
          open_questions: [],
          next_steps: ["确认负责人"],
          notice: "",
        },
      },
    });

    expect(state.status).toBe("completed");
    expect(state.content?.next_steps).toEqual(["确认负责人"]);
  });
});
