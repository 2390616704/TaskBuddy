"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createConversation,
  listConversations,
  listMessages,
  retryMessage,
} from "@/features/conversations/api";
import type { Conversation, Message } from "@/features/conversations/types";
import { useConversationStream } from "@/features/conversations/use-conversation-stream";

import { AgentHeader } from "./agent-header";
import { Composer } from "./composer";
import { ConversationSidebar } from "./conversation-sidebar";
import { MessageList } from "./message-list";

export function ChatApp() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pendingUserText, setPendingUserText] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retrying, setRetrying] = useState(false);

  const refreshMessages = useCallback(async (conversationId: string) => {
    setMessages(await listMessages(conversationId));
  }, []);

  const refreshConversations = useCallback(async () => {
    setConversations(await listConversations());
  }, []);

  const onSettled = useCallback(
    async (conversationId: string) => {
      await Promise.all([
        refreshMessages(conversationId),
        refreshConversations(),
      ]);
      setPendingUserText("");
    },
    [refreshConversations, refreshMessages],
  );
  const stream = useConversationStream({ onSettled });

  useEffect(() => {
    void (async () => {
      try {
        const loaded = await listConversations();
        setConversations(loaded);
        if (loaded[0]) {
          setCurrentId(loaded[0].id);
          await refreshMessages(loaded[0].id);
        }
      } catch {
        setError("无法加载会话，请确认后端服务已启动。");
      } finally {
        setLoading(false);
      }
    })();
  }, [refreshMessages]);

  const selectConversation = async (conversationId: string) => {
    if (stream.isRunning) return;
    setCurrentId(conversationId);
    setSidebarOpen(false);
    setError("");
    try {
      await refreshMessages(conversationId);
    } catch {
      setError("无法读取会话历史。");
    }
  };

  const newConversation = async () => {
    setError("");
    try {
      const created = await createConversation();
      setConversations((current) => [created, ...current]);
      setCurrentId(created.id);
      setMessages([]);
      setSidebarOpen(false);
      await refreshMessages(created.id);
    } catch {
      setError("无法创建会话。");
    }
  };

  const send = async (content: string) => {
    if (!currentId) return;
    setPendingUserText(content);
    setError("");
    await stream.send(currentId, content);
  };

  const retry = async (messageId: string) => {
    if (!currentId || retrying) return;
    setRetrying(true);
    setError("");
    const controller = new AbortController();
    try {
      await retryMessage(
        currentId,
        messageId,
        controller.signal,
        () => undefined,
      );
      await onSettled(currentId);
    } catch {
      setError("重试失败，请稍后再试。");
    } finally {
      setRetrying(false);
    }
  };

  const renderedMessages = useMemo(() => {
    const transient: Message[] = [];
    if (pendingUserText) {
      transient.push({
        id: "pending-user",
        conversationId: currentId ?? "",
        role: "user",
        content: pendingUserText,
        status: "completed",
        inReplyToMessageId: null,
        retryOfMessageId: null,
        errorCode: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
    if (stream.state.messageId && stream.state.status === "streaming") {
      transient.push({
        id: stream.state.messageId,
        conversationId: currentId ?? "",
        role: "assistant",
        content: stream.state.text,
        status: "streaming",
        inReplyToMessageId: stream.state.userMessageId,
        retryOfMessageId: null,
        errorCode: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
    return [...messages, ...transient];
  }, [currentId, messages, pendingUserText, stream.state]);

  const current = conversations.find(
    (conversation) => conversation.id === currentId,
  );

  return (
    <div className="app-shell">
      <ConversationSidebar
        conversations={conversations}
        currentId={currentId}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onCreate={() => void newConversation()}
        onSelect={(id) => void selectConversation(id)}
      />
      {sidebarOpen ? (
        <button
          className="sidebar-backdrop"
          aria-label="关闭会话列表"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <main className="chat-panel">
        <AgentHeader
          title={current?.title ?? "工作事项助手"}
          onOpenSidebar={() => setSidebarOpen(true)}
        />
        {error ? (
          <div className="error-banner" role="alert">
            {error}
          </div>
        ) : null}
        {loading ? (
          <div className="loading-state" role="status">
            正在加载会话…
          </div>
        ) : !currentId ? (
          <div className="empty-chat">
            <span className="empty-icon" aria-hidden="true">
              ✦
            </span>
            <h2>开始第一段对话</h2>
            <p>创建会话后，即可使用 Mock 模式验证完整流程。</p>
            <button
              className="button button-primary"
              type="button"
              onClick={() => void newConversation()}
            >
              新建会话
            </button>
          </div>
        ) : (
          <MessageList
            messages={renderedMessages}
            onRetry={(id) => void retry(id)}
          />
        )}
        <Composer
          disabled={!currentId || loading || retrying}
          running={stream.isRunning}
          onSend={send}
          onCancel={stream.cancel}
        />
      </main>
    </div>
  );
}
