import { createSseParser, type RawSseEvent } from "./sse";
import type { Conversation, Message, StreamEvent } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly requestId: string,
    readonly status: number,
  ) {
    super(message);
  }
}

type ErrorEnvelope = {
  error: { code: string; message: string; requestId: string };
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function hasString(value: Record<string, unknown>, key: string): boolean {
  return typeof value[key] === "string";
}

function toStreamEvent(raw: RawSseEvent): StreamEvent {
  if (!isRecord(raw.data)) {
    throw new Error(`Invalid SSE data for ${raw.name}`);
  }
  const data = raw.data;
  switch (raw.name) {
    case "message.accepted":
      if (
        hasString(data, "requestId") &&
        hasString(data, "userMessageId") &&
        hasString(data, "messageId")
      ) {
        return { name: raw.name, data } as StreamEvent;
      }
      break;
    case "message.delta":
      if (
        hasString(data, "messageId") &&
        typeof data.sequence === "number" &&
        hasString(data, "delta")
      ) {
        return { name: raw.name, data } as StreamEvent;
      }
      break;
    case "message.completed":
      if (
        hasString(data, "messageId") &&
        data.status === "completed" &&
        hasString(data, "content")
      ) {
        return { name: raw.name, data } as StreamEvent;
      }
      break;
    case "message.cancelled":
      if (hasString(data, "messageId") && data.status === "cancelled") {
        return { name: raw.name, data } as StreamEvent;
      }
      break;
    case "message.error":
      if (
        hasString(data, "messageId") &&
        hasString(data, "code") &&
        hasString(data, "message") &&
        hasString(data, "requestId") &&
        typeof data.retryable === "boolean"
      ) {
        return { name: raw.name, data } as StreamEvent;
      }
      break;
    case "heartbeat":
      return { name: raw.name, data: {} };
    default:
      throw new Error(`Unsupported SSE event: ${raw.name}`);
  }
  throw new Error(`Invalid SSE data for ${raw.name}`);
}

async function apiError(response: Response): Promise<ApiError> {
  const body = (await response.json()) as ErrorEnvelope;
  return new ApiError(
    body.error.code,
    body.error.message,
    body.error.requestId,
    response.status,
  );
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) throw await apiError(response);
  return (await response.json()) as T;
}

export async function readStreamEvents(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.ok) throw await apiError(response);
  if (!response.body) throw new Error("SSE response has no body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSseParser();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const raw of parser.push(decoder.decode(value, { stream: true }))) {
      onEvent(toStreamEvent(raw));
    }
  }
  for (const raw of parser.push(decoder.decode())) {
    onEvent(toStreamEvent(raw));
  }
}

export type SendMessageInput = {
  conversationId: string;
  content: string;
  clientMessageId: string;
  signal: AbortSignal;
};

export async function sendMessage(
  input: SendMessageInput,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${input.conversationId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: input.content,
        agentId: "work-assistant",
        clientMessageId: input.clientMessageId,
      }),
      signal: input.signal,
    },
  );
  await readStreamEvents(response, onEvent);
}

export function listConversations(): Promise<Conversation[]> {
  return requestJson("/api/conversations");
}

export function createConversation(providerId = "mock"): Promise<Conversation> {
  return requestJson("/api/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ agentId: "work-assistant", providerId }),
  });
}

export function listMessages(conversationId: string): Promise<Message[]> {
  return requestJson(`/api/conversations/${conversationId}/messages`);
}

export function cancelMessage(
  conversationId: string,
  messageId: string,
): Promise<{ messageId: string; status: "cancelled" }> {
  return requestJson(
    `/api/conversations/${conversationId}/messages/${messageId}/cancel`,
    { method: "POST" },
  );
}

export async function retryMessage(
  conversationId: string,
  messageId: string,
  signal: AbortSignal,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/conversations/${conversationId}/messages/${messageId}/retry`,
    { method: "POST", signal },
  );
  await readStreamEvents(response, onEvent);
}
