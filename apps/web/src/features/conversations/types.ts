export type MessageStatus =
  "pending" | "streaming" | "completed" | "cancelled" | "failed";

export type WorkAssistantResponse = {
  mode: "answer" | "clarification" | "refusal";
  conclusion: string;
  risks: string[];
  open_questions: string[];
  next_steps: string[];
  notice: string;
};

export type Conversation = {
  id: string;
  agentId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
};

export type Message = {
  id: string;
  conversationId: string;
  role: "user" | "assistant";
  content: string | WorkAssistantResponse;
  status: MessageStatus;
  inReplyToMessageId: string | null;
  retryOfMessageId: string | null;
  errorCode: string | null;
  createdAt: string;
  updatedAt: string;
};

export type StreamEvent =
  | {
      name: "message.accepted";
      data: { requestId: string; userMessageId: string; messageId: string };
    }
  | {
      name: "message.delta";
      data: { messageId: string; sequence: number; delta: string };
    }
  | {
      name: "message.completed";
      data: {
        messageId: string;
        status: "completed";
        content: WorkAssistantResponse;
      };
    }
  | {
      name: "message.cancelled";
      data: { messageId: string; status: "cancelled" };
    }
  | {
      name: "message.error";
      data: {
        messageId: string;
        code: string;
        message: string;
        requestId: string;
        retryable: boolean;
      };
    }
  | { name: "heartbeat"; data: Record<string, never> };
