import type { ProviderInfo } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export async function listProviders(): Promise<ProviderInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/providers`);
  if (!response.ok) throw new Error("无法读取模型列表");
  return (await response.json()) as ProviderInfo[];
}
