export type RawSseEvent = {
  name: string;
  data: unknown;
};

export type SseParser = {
  push(chunk: string): RawSseEvent[];
};

export function createSseParser(): SseParser {
  let buffer = "";

  return {
    push(chunk: string): RawSseEvent[] {
      buffer = (buffer + chunk).replaceAll("\r\n", "\n");
      const parsed: RawSseEvent[] = [];
      let boundary = buffer.indexOf("\n\n");

      while (boundary >= 0) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const lines = block.split("\n");
        const eventLine = lines.find((line) => line.startsWith("event: "));
        const dataLines = lines
          .filter((line) => line.startsWith("data: "))
          .map((line) => line.slice("data: ".length));
        if (eventLine && dataLines.length > 0) {
          parsed.push({
            name: eventLine.slice("event: ".length),
            data: JSON.parse(dataLines.join("\n")) as unknown,
          });
        }
        boundary = buffer.indexOf("\n\n");
      }
      return parsed;
    },
  };
}
