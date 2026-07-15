import type { Message } from "@/features/conversations/types";

import { MarkdownText } from "./markdown-text";

type MessageCardProps = {
  message: Message;
  onRetry?(messageId: string): void;
};

const statusLabels = {
  pending: "发送中",
  streaming: "生成中",
  completed: "已完成",
  cancelled: "已取消",
  failed: "生成失败",
} as const;

export function MessageCard({ message, onRetry }: MessageCardProps) {
  return (
    <article
      className={`message message-${message.role}`}
      aria-label={`${message.role === "user" ? "用户" : "助手"}消息`}
    >
      <div className="message-body">
        <MarkdownText>
          {message.content || (message.status === "pending" ? "等待生成…" : "")}
        </MarkdownText>
      </div>
      <footer className="message-meta">
        <span>{statusLabels[message.status]}</span>
        {message.status === "failed" && onRetry ? (
          <button
            className="text-button"
            type="button"
            onClick={() => onRetry(message.id)}
          >
            重试
          </button>
        ) : null}
      </footer>
    </article>
  );
}
