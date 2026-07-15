import { describe, expect, it } from "vitest";

import { readStreamEvents } from "./api";
import type { StreamEvent } from "./types";

describe("readStreamEvents", () => {
  it("decodes UTF-8 and SSE boundaries split across byte chunks", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode("event: message.del"));
        controller.enqueue(
          encoder.encode(
            'ta\ndata: {"messageId":"m1","sequence":1,"delta":"风险"}\n\n',
          ),
        );
        controller.close();
      },
    });
    const events: StreamEvent[] = [];

    await readStreamEvents(new Response(body), (event) => events.push(event));

    expect(events).toEqual([
      {
        name: "message.delta",
        data: { messageId: "m1", sequence: 1, delta: "风险" },
      },
    ]);
  });

  it("rejects an unknown event instead of guessing its shape", async () => {
    const body = new Response('event: provider.raw\ndata: {"secret":true}\n\n');

    await expect(readStreamEvents(body, () => undefined)).rejects.toThrow(
      "Unsupported SSE event: provider.raw",
    );
  });
});
