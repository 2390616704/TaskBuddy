import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 812 } },
    },
  ],
  webServer: [
    {
      command: "corepack pnpm dev:api",
      url: "http://127.0.0.1:8000/health",
      env: { DATABASE_URL: "sqlite+aiosqlite:///./test-results/e2e.db" },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "corepack pnpm dev:web",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
