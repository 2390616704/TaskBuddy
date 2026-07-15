import { expect, test, type Page } from "@playwright/test";

async function createNewConversation(page: Page) {
  const menu = page.getByRole("button", { name: "打开会话列表" });
  if (await menu.isVisible()) await menu.click();
  await page
    .getByRole("complementary", { name: "会话列表" })
    .getByRole("button", { name: "新建会话" })
    .click();
}

test("completes the first Mock conversation without a key", async ({ page }) => {
  await page.goto("/");

  await createNewConversation(page);
  await page.getByRole("textbox", { name: "消息" }).fill("帮我梳理本周发布风险");
  await page.getByRole("button", { name: "发送" }).click();

  await expect(page.getByRole("heading", { name: "结论" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "风险项" })).toBeVisible();
  await expect(page.getByLabel("助手消息").getByText("已完成")).toBeVisible();
});

test("cancels a slow generation and keeps the state after refresh", async ({ page }) => {
  await page.goto("/");
  await createNewConversation(page);
  await page
    .getByRole("textbox", { name: "消息" })
    .fill("[mock:slow] 帮我梳理本周发布风险");
  await page.getByRole("button", { name: "发送" }).click();
  await page.getByRole("button", { name: "停止生成" }).click();

  await expect(page.getByText("已取消")).toBeVisible();
  await page.reload();
  await expect(page.getByText("已取消")).toBeVisible();
});

test("renders a usable mobile layout", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-only visual assertion");
  await page.goto("/");

  await expect(page.getByRole("button", { name: "打开会话列表" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "消息" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "消息" })).toBeInViewport();
});
