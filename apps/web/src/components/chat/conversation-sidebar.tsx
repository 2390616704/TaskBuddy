import type { Conversation } from "@/features/conversations/types";

type Props = {
  conversations: Conversation[];
  currentId: string | null;
  open: boolean;
  onClose(): void;
  onCreate(): void;
  onSelect(conversationId: string): void;
};

export function ConversationSidebar({
  conversations,
  currentId,
  open,
  onClose,
  onCreate,
  onSelect,
}: Props) {
  return (
    <aside
      className={`conversation-sidebar ${open ? "sidebar-open" : ""}`}
      aria-label="会话列表"
    >
      <div className="sidebar-heading">
        <span className="brand-mark" aria-hidden="true">
          T
        </span>
        <strong>TaskBuddy</strong>
        <button
          className="sidebar-close"
          type="button"
          aria-label="关闭会话列表"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <button
        className="button button-primary new-conversation"
        type="button"
        onClick={onCreate}
      >
        ＋ 新建会话
      </button>
      <p className="sidebar-label">最近会话</p>
      <nav>
        {conversations.length ? (
          conversations.map((conversation) => (
            <button
              className={`conversation-item ${currentId === conversation.id ? "conversation-active" : ""}`}
              type="button"
              key={conversation.id}
              aria-current={currentId === conversation.id ? "page" : undefined}
              onClick={() => onSelect(conversation.id)}
            >
              <span>{conversation.title}</span>
              <time>
                {new Date(conversation.updatedAt).toLocaleDateString("zh-CN")}
              </time>
            </button>
          ))
        ) : (
          <p className="sidebar-empty">暂无会话</p>
        )}
      </nav>
    </aside>
  );
}
