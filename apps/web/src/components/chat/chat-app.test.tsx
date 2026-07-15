import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/features/conversations/api";

import { ChatApp } from "./chat-app";

vi.mock("@/features/conversations/api", async () => {
  const actual = await vi.importActual<
    typeof import("@/features/conversations/api")
  >("@/features/conversations/api");
  return {
    ...actual,
    listConversations: vi.fn(),
    createConversation: vi.fn(),
    listMessages: vi.fn(),
  };
});

describe("ChatApp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listConversations).mockResolvedValue([]);
    vi.mocked(api.listMessages).mockResolvedValue([]);
  });

  it("shows an empty state and creates the first conversation", async () => {
    vi.mocked(api.createConversation).mockResolvedValue({
      id: "c1",
      agentId: "work-assistant",
      title: "新会话",
      createdAt: "2026-07-15T12:00:00Z",
      updatedAt: "2026-07-15T12:00:00Z",
    });
    render(<ChatApp />);

    expect(await screen.findByText("开始第一段对话")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "新建会话" }));

    await waitFor(() => expect(api.createConversation).toHaveBeenCalledOnce());
    expect(screen.getByRole("heading", { name: "新会话" })).toBeVisible();
    expect(api.listMessages).toHaveBeenCalledWith("c1");
  });
});
