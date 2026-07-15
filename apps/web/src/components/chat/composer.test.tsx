import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Composer } from "./composer";

describe("Composer", () => {
  it("sends on Enter and inserts a newline on Shift+Enter", async () => {
    const send = vi.fn();
    render(
      <Composer
        disabled={false}
        running={false}
        onSend={send}
        onCancel={vi.fn()}
      />,
    );
    const input = screen.getByRole("textbox", { name: "消息" });

    await userEvent.type(
      input,
      "发布风险{shift>}{enter}{/shift}补充信息{enter}",
    );

    expect(send).toHaveBeenCalledWith("发布风险\n补充信息");
    expect(input).toHaveValue("");
  });

  it("does not submit whitespace", async () => {
    const send = vi.fn();
    render(
      <Composer
        disabled={false}
        running={false}
        onSend={send}
        onCancel={vi.fn()}
      />,
    );

    await userEvent.type(
      screen.getByRole("textbox", { name: "消息" }),
      "   {enter}",
    );

    expect(send).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("请输入工作问题");
  });

  it("shows a stop action while generation is running", async () => {
    const cancel = vi.fn();
    render(
      <Composer disabled={false} running onSend={vi.fn()} onCancel={cancel} />,
    );

    await userEvent.click(screen.getByRole("button", { name: "停止生成" }));

    expect(cancel).toHaveBeenCalledOnce();
  });
});
