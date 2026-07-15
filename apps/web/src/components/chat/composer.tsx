"use client";

import { useState } from "react";

type ComposerProps = {
  disabled: boolean;
  running: boolean;
  providerLabel?: string;
  onSend(content: string): void | Promise<void>;
  onCancel(): void | Promise<void>;
};

export function Composer({
  disabled,
  running,
  providerLabel = "Mock",
  onSend,
  onCancel,
}: ComposerProps) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");

  const submit = () => {
    const content = value.trim();
    if (!content) {
      setError("请输入工作问题");
      return;
    }
    if (disabled || running) return;
    setError("");
    setValue("");
    void onSend(content);
  };

  return (
    <div className="composer">
      <label className="sr-only" htmlFor="message-composer">
        消息
      </label>
      <textarea
        id="message-composer"
        aria-label="消息"
        disabled={disabled || running}
        value={value}
        placeholder="输入工作问题，Enter 发送，Shift+Enter 换行"
        rows={3}
        onChange={(event) => {
          setValue(event.target.value);
          if (error) setError("");
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <div className="composer-footer">
        <span className="composer-hint">
          {providerLabel} · 不执行真实操作
        </span>
        {running ? (
          <button
            className="button button-danger"
            type="button"
            onClick={() => void onCancel()}
          >
            停止生成
          </button>
        ) : (
          <button
            className="button button-primary"
            type="button"
            disabled={disabled}
            onClick={submit}
          >
            发送
          </button>
        )}
      </div>
      {error ? (
        <p className="field-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
