"use client";

import { useCallback, useRef, useState } from "react";

import { cancelMessage, sendMessage } from "./api";
import {
  initialStreamState,
  reduceStreamEvent,
  type StreamState,
} from "./stream-state";
import type { StreamEvent } from "./types";

type Options = {
  onSettled(conversationId: string): Promise<void>;
};

export function useConversationStream({ onSettled }: Options) {
  const [state, setState] = useState<StreamState>(initialStreamState);
  const controller = useRef<AbortController | null>(null);
  const activeConversationId = useRef<string | null>(null);
  const activeMessageId = useRef<string | null>(null);

  const send = useCallback(
    async (conversationId: string, content: string) => {
      const abortController = new AbortController();
      controller.current = abortController;
      activeConversationId.current = conversationId;
      activeMessageId.current = null;
      setState(initialStreamState);
      let reachedTerminalState = false;

      const onEvent = (event: StreamEvent) => {
        if (event.name === "message.accepted") {
          activeMessageId.current = event.data.messageId;
        }
        if (
          event.name === "message.completed" ||
          event.name === "message.cancelled" ||
          event.name === "message.error"
        ) {
          reachedTerminalState = true;
        }
        setState((previous) => reduceStreamEvent(previous, event));
      };

      try {
        await sendMessage(
          {
            conversationId,
            content,
            clientMessageId: crypto.randomUUID(),
            signal: abortController.signal,
          },
          onEvent,
        );
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setState((previous) => ({
            ...previous,
            status: "failed",
            error: {
              code: "NETWORK_ERROR",
              message: "无法连接服务，请稍后重试。",
              retryable: true,
            },
          }));
          reachedTerminalState = true;
        }
      } finally {
        controller.current = null;
        if (reachedTerminalState) await onSettled(conversationId);
      }
    },
    [onSettled],
  );

  const cancel = useCallback(async () => {
    const conversationId = activeConversationId.current;
    const messageId = activeMessageId.current;
    if (!conversationId || !messageId) return;
    await cancelMessage(conversationId, messageId);
    setState((previous) => ({ ...previous, status: "cancelled" }));
    controller.current?.abort();
    await onSettled(conversationId);
  }, [onSettled]);

  return { state, send, cancel, isRunning: state.status === "streaming" };
}
