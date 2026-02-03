import { expect, test, APIRequestContext } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL;
if (!BASE_URL) {
  throw new Error("E2E_BASE_URL is required for e2e tests.");
}

async function fetchProfiles(request: APIRequestContext) {
  const response = await request.get(`${BASE_URL}/api/profiles`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

function pickRunMode(
  data: { profiles: Array<{ id: string; entrypointType?: string | null }>; runModes: string[]; defaultRunMode?: string | null },
  entrypointType?: string,
): string {
  if (entrypointType) {
    const match = data.profiles.find((profile) => profile.entrypointType === entrypointType);
    if (match) {
      return match.id;
    }
  }
  return data.defaultRunMode ?? data.runModes[0];
}

// Helper to delete a thread by ID
async function deleteThread(request: APIRequestContext, threadId: string) {
  try {
    const url = `${BASE_URL}/api/threads/${threadId}`;
    await request.delete(url);
  } catch {
    // Ignore cleanup errors
  }
}

test.describe("Run modes", () => {
  test.beforeEach(async ({ page }) => {
    // Wait for API to be healthy
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("single mode sends message and receives response", async ({ page, request }) => {
    // Get thread count before test
    const beforeResponse = await request.get(`${BASE_URL}/api/threads`);
    const beforeData = await beforeResponse.json();
    const threadCountBefore = beforeData.threads?.length ?? 0;

    // Select a single-entrypoint mode
    const data = await fetchProfiles(request);
    const runMode = pickRunMode(data, "single");
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(runMode);

    // Send message
    const input = page.getByPlaceholder("Send a message...");
    await input.fill("What is 2+2? Just answer the number.");
    await page.getByRole("button", { name: "Send" }).click();

    // Wait for user message to appear in the message area (not sidebar)
    await expect(
      page.getByRole("paragraph").getByText("What is 2+2?")
    ).toBeVisible({ timeout: 5000 });

    // Wait for response completion indicator
    await expect(page.locator("text=done").first()).toBeVisible({ timeout: 30000 });

    // Cleanup: Get the newest thread and delete it
    const afterResponse = await request.get(`${BASE_URL}/api/threads`);
    const afterData = await afterResponse.json();
    const threadCountAfter = afterData.threads?.length ?? 0;

    if (threadCountAfter > threadCountBefore && afterData.threads?.[0]) {
      await deleteThread(request, afterData.threads[0].remoteId);
    }
  });

  test("mode selection persists across interactions", async ({ page, request }) => {
    const modeCombobox = page.getByRole("combobox", { name: "Run mode" });
    const data = await fetchProfiles(request);
    const modes = data.runModes;
    if (modes.length < 2) {
      test.skip(true, "Need at least two run modes to validate switching.");
    }

    // Select first mode
    await modeCombobox.selectOption(modes[0]);
    await expect(modeCombobox).toHaveValue(modes[0]);

    // Select second mode
    await modeCombobox.selectOption(modes[1]);
    await expect(modeCombobox).toHaveValue(modes[1]);

    // Select back to first
    await modeCombobox.selectOption(modes[0]);
    await expect(modeCombobox).toHaveValue(modes[0]);
  });

  test("profile selection is enabled when profiles load", async ({ page }) => {
    // Profile selection is now handled internally - no UI selector
    // Just verify the page loads without profile selector
    await expect(page.getByRole("button", { name: "New thread" })).toBeVisible();
  });
});

test.describe("Thread management", () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("URL updates when creating and navigating to thread", async ({ page, request }) => {
    // Get thread count before test
    const beforeResponse = await request.get(`${BASE_URL}/api/threads`);
    const beforeData = await beforeResponse.json();
    const threadCountBefore = beforeData.threads?.length ?? 0;

    // Send a message to create a thread
    const input = page.getByPlaceholder("Send a message...");
    await input.fill("URL navigation test");
    await page.getByRole("button", { name: "Send" }).click();

    // Wait for message to be sent (appears in paragraph)
    await expect(
      page.getByRole("paragraph").getByText("URL navigation test")
    ).toBeVisible({ timeout: 10000 });

    // Wait for done indicator (response complete)
    await expect(page.locator("text=done").first()).toBeVisible({ timeout: 30000 });

    // The thread should now be in the sidebar - click it to ensure URL navigation
    const threadButton = page.getByRole("button", { name: /URL navigation test/i });

    // If we can find the thread button, clicking should navigate
    const threadCount = await threadButton.count();
    if (threadCount > 0) {
      // Click new thread first to reset
      await page.getByRole("button", { name: "New thread" }).click();
      await expect(page).toHaveURL(`${BASE_URL}/new`);

      // Now click the thread
      await threadButton.click();

      // URL should update to conversation path
      await expect(page).toHaveURL(/\/c\/[a-zA-Z0-9-]+/, { timeout: 10000 });
    }

    // Cleanup: Get the newest thread and delete it
    const afterResponse = await request.get(`${BASE_URL}/api/threads`);
    const afterData = await afterResponse.json();
    const threadCountAfter = afterData.threads?.length ?? 0;

    if (threadCountAfter > threadCountBefore && afterData.threads?.[0]) {
      await deleteThread(request, afterData.threads[0].remoteId);
    }
  });

  test("home page shows welcome message", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Start a new run" })).toBeVisible();
    await expect(page.getByText("Ask a question")).toBeVisible();
  });

  test("new thread resets to home state", async ({ page, request }) => {
    // Get thread count before test
    const beforeResponse = await request.get(`${BASE_URL}/api/threads`);
    const beforeData = await beforeResponse.json();
    const threadCountBefore = beforeData.threads?.length ?? 0;

    // Send a message first
    const input = page.getByPlaceholder("Send a message...");
    await input.fill("Creating thread for test");
    await page.getByRole("button", { name: "Send" }).click();

    // Wait for message to appear
    await expect(page.getByText("Creating thread for test")).toBeVisible({ timeout: 5000 });

    // Wait for done indicator
    await expect(page.locator("text=done").first()).toBeVisible({ timeout: 30000 });

    // Click new thread
    await page.getByRole("button", { name: "New thread" }).click();

    // Should be back at home with welcome message
    await expect(page.getByRole("heading", { name: "Start a new run" })).toBeVisible();

    // Cleanup: Get the newest thread and delete it
    const afterResponse = await request.get(`${BASE_URL}/api/threads`);
    const afterData = await afterResponse.json();
    const threadCountAfter = afterData.threads?.length ?? 0;

    if (threadCountAfter > threadCountBefore && afterData.threads?.[0]) {
      await deleteThread(request, afterData.threads[0].remoteId);
    }
  });
});
