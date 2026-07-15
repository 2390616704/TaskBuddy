import type {
  MessageStatus,
  StreamEvent,
  WorkAssistantResponse,
} from "./types";

export type StreamState = {
  requestId: string | null;
  userMessageId: string | null;
  messageId: string | null;
  text: string;
  lastSequence: number;
  status: MessageStatus | "idle";
  content: WorkAssistantResponse | null;
  error: { code: string; message: string; retryable: boolean } | null;
};

export const initialStreamState: StreamState = {
  requestId: null,
  userMessageId: null,
  messageId: null,
  text: "",
  lastSequence: 0,
  status: "idle",
  content: null,
  error: null,
};

export function reduceStreamEvent(
  state: StreamState,
  event: StreamEvent,
): StreamState {
  switch (event.name) {
    case "message.accepted":
      return {
        ...initialStreamState,
        requestId: event.data.requestId,
        userMessageId: event.data.userMessageId,
        messageId: event.data.messageId,
        status: "streaming",
      };
    case "message.delta":
      if (
        event.data.messageId !== state.messageId ||
        event.data.sequence <= state.lastSequence
      ) {
        return state;
      }
      return {
        ...state,
        text: state.text + event.data.delta,
        lastSequence: event.data.sequence,
      };
    case "message.completed":
      return {
        ...state,
        messageId: event.data.messageId,
        status: "completed",
        content: event.data.content,
        error: null,
      };
    case "message.cancelled":
      return {
        ...state,
        messageId: event.data.messageId,
        status: "cancelled",
      };
    case "message.error":
      return {
        ...state,
        messageId: event.data.messageId,
        status: "failed",
        error: {
          code: event.data.code,
          message: event.data.message,
          retryable: event.data.retryable,
        },
      };
    case "heartbeat":
      return state;
  }
}
