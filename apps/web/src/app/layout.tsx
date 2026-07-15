import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "TaskBuddy",
  description: "工作事项助手",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
