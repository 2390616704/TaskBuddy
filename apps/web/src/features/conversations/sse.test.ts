import { describe, expect, it } from "vitest";

import { createSseParser } from "./sse";

describe("createSseParser", () => {
  it("parses an event split across network chunks", () => {
    const parser = createSseParser();

    expect(parser.push("event: message.del")).toEqual([]);
    expect(
      parser.push('ta\ndata: {"messageId":"m1","sequence":1,"delta":"你"}\n\n'),
    ).toEqual([
      {
        name: "message.delta",
        data: { messageId: "m1", sequence: 1, delta: "你" },
      },
    ]);
  });

  it("parses several named events from one chunk", () => {
    const parser = createSseParser();

    expect(
      parser.push(
        'event: heartbeat\ndata: {}\n\nevent: message.cancelled\ndata: {"messageId":"m1","status":"cancelled"}\n\n',
      ),
    ).toHaveLength(2);
  });

  it("normalizes CRLF even when the pair is split across chunks", () => {
    const parser = createSseParser();

    expect(parser.push("event: heartbeat\r")).toEqual([]);
    expect(parser.push("\ndata: {}\r")).toEqual([]);
    expect(parser.push("\n\r\n")).toEqual([{ name: "heartbeat", data: {} }]);
  });
});
