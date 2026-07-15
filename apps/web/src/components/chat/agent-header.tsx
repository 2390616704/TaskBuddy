import type { ProviderInfo } from "@/features/providers/types";

import { ProviderPicker } from "./provider-picker";

type Props = {
  title: string;
  currentProvider?: ProviderInfo;
  providers: ProviderInfo[];
  providerDisabled: boolean;
  onOpenSidebar(): void;
  onSelectProvider(providerId: string): void;
};

export function AgentHeader({
  title,
  currentProvider,
  providers,
  providerDisabled,
  onOpenSidebar,
  onSelectProvider,
}: Props) {
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
      <ProviderPicker
        current={currentProvider}
        providers={providers}
        disabled={providerDisabled}
        onSelect={onSelectProvider}
      />
    </header>
  );
}
