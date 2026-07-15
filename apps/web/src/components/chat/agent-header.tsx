type Props = {
  title: string;
  onOpenSidebar(): void;
};

export function AgentHeader({ title, onOpenSidebar }: Props) {
  return (
    <header className="agent-header">
      <button
        className="menu-button"
        type="button"
        aria-label="打开会话列表"
        onClick={onOpenSidebar}
      >
        ☰
      </button>
      <div>
        <p className="eyebrow">工作事项助手</p>
        <h1>{title}</h1>
        <p className="agent-description">
          梳理风险、澄清信息并给出下一步；不会执行真实操作。
        </p>
      </div>
      <span className="mode-badge">
        <span aria-hidden="true">●</span> Mock
      </span>
    </header>
  );
}
