"use client";

import { useEffect, useRef } from "react";

import type { Message } from "@/features/conversations/types";

import { MessageCard } from "./message-card";

type Props = {
  messages: Message[];
  onRetry(messageId: string): void;
};

export function MessageList({ messages, onRetry }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const wasNearBottom = useRef(true);

  useEffect(() => {
    const element = viewport.current;
    if (element && wasNearBottom.current)
      element.scrollTop = element.scrollHeight;
  }, [messages]);

  if (!messages.length) {
    return (
      <div className="empty-chat">
        <span className="empty-icon" aria-hidden="true">
          ✦
        </span>
        <h2>开始第一段对话</h2>
        <p>可以试试：“帮我梳理本周发布风险”。</p>
      </div>
    );
  }

  return (
    <div
      className="message-list"
      ref={viewport}
      aria-live="polite"
      onScroll={(event) => {
        const element = event.currentTarget;
        wasNearBottom.current =
          element.scrollHeight - element.scrollTop - element.clientHeight < 80;
      }}
    >
      <div className="message-column">
        {messages.map((message) => (
          <MessageCard key={message.id} message={message} onRetry={onRetry} />
        ))}
      </div>
    </div>
  );
}
