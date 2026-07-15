"use client";

import { useEffect, useRef, useState } from "react";

import type { ProviderInfo } from "@/features/providers/types";

type Props = {
  current?: ProviderInfo;
  providers: ProviderInfo[];
  disabled: boolean;
  onSelect(providerId: string): void;
};

export function ProviderPicker({
  current,
  providers,
  disabled,
  onSelect,
}: Props) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  return (
    <div className="provider-picker" ref={container}>
      <button
        className="mode-badge"
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
      >
        <span aria-hidden="true">●</span>
        {current?.displayName ?? "选择模型"}
        <span aria-hidden="true">⌄</span>
      </button>
      {open ? (
        <div className="provider-menu" role="listbox" aria-label="新会话模型">
          <p>选择模型并新建会话</p>
          {providers.map((provider) => (
            <button
              type="button"
              role="option"
              aria-selected={provider.id === current?.id}
              disabled={!provider.available}
              key={provider.id}
              onClick={() => {
                setOpen(false);
                onSelect(provider.id);
              }}
            >
              <span>{provider.displayName}</span>
              <small>
                {provider.available ? provider.modelName : "未配置"}
              </small>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
