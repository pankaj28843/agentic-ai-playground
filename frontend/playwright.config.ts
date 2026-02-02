import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL;
if (!baseURL) {
  throw new Error("E2E_BASE_URL is required to run Playwright tests.");
}

export default defineConfig({
  testDir: "./apps/web/tests/e2e",
  fullyParallel: false, // Run tests sequentially to avoid race conditions with shared backend state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  timeout: 60_000, // Increased timeout for LLM responses
  expect: {
    timeout: 30_000, // Assertions can wait longer for streaming responses
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
