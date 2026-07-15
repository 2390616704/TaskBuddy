import type {
  Message,
  WorkAssistantResponse,
} from "@/features/conversations/types";

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

function StructuredAnswer({ content }: { content: WorkAssistantResponse }) {
  return (
    <div className="structured-answer">
      {content.conclusion ? (
        <section>
          <h3>结论</h3>
          <p>{content.conclusion}</p>
        </section>
      ) : null}
      {content.risks.length ? (
        <section>
          <h3>风险项</h3>
          <ul>
            {content.risks.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {content.open_questions.length ? (
        <section>
          <h3>待确认项</h3>
          <ul>
            {content.open_questions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
      {content.next_steps.length ? (
        <section>
          <h3>下一步</h3>
          <ol>
            {content.next_steps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ol>
        </section>
      ) : null}
      {content.notice ? (
        <p className="message-notice">{content.notice}</p>
      ) : null}
    </div>
  );
}

export function MessageCard({ message, onRetry }: MessageCardProps) {
  return (
    <article
      className={`message message-${message.role}`}
      aria-label={`${message.role === "user" ? "用户" : "助手"}消息`}
    >
      <div className="message-body">
        {typeof message.content === "object" ? (
          <StructuredAnswer content={message.content} />
        ) : (
          <p className="message-text">
            {message.content ||
              (message.status === "pending" ? "等待生成…" : "")}
          </p>
        )}
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
