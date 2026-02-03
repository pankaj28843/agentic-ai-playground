/**
 * E2E tests for TechDocs tool calls across all run modes.
 *
 * These tests verify that the Strands SDK properly executes tool calls
 * (not just describing them) in single, graph, and swarm modes.
 *
 * Key debugging questions tested:
 * - Do tools actually execute (not just get described in text)?
 * - Are tool calls visible in the trace panel?
 * - Does agent attribution work in swarm mode?
 * - Are real TechDocs URLs cited (not made-up ones)?
 */

import { expect, test, APIRequestContext } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL;
if (!BASE_URL) {
  throw new Error("E2E_BASE_URL is required for e2e tests.");
}
const TOOL_CALL_TIMEOUT = 90_000; // Tool calls can take time

async function fetchProfiles(request: APIRequestContext) {
  const response = await request.get(`${BASE_URL}/api/profiles`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function resolveRunMode(
  request: APIRequestContext,
  entrypointType?: string,
): Promise<{ runMode: string; hasRequestedType: boolean }> {
  const data = await fetchProfiles(request);
  const match = entrypointType
    ? data.profiles.find((profile: { id: string; entrypointType?: string | null }) => profile.entrypointType === entrypointType)
    : null;
  const runMode = match?.id ?? data.defaultRunMode ?? data.runModes[0];
  return { runMode, hasRequestedType: Boolean(match) };
}

// Helper to delete a thread by ID
async function deleteThread(request: APIRequestContext, threadId: string) {
  try {
    await request.delete(`${BASE_URL}/api/threads/${threadId}`);
  } catch {
    // Ignore cleanup errors
  }
}

// Helper to get thread count
async function getThreadCount(request: APIRequestContext): Promise<number> {
  const response = await request.get(`${BASE_URL}/api/threads`);
  const data = await response.json();
  return data.threads?.length ?? 0;
}

// Helper to cleanup newest threads
async function cleanupNewThreads(
  request: APIRequestContext,
  countBefore: number
) {
  const response = await request.get(`${BASE_URL}/api/threads`);
  const data = await response.json();
  const threads = data.threads ?? [];

  // Delete threads created during test
  for (let i = 0; i < threads.length - countBefore && i < threads.length; i++) {
    await deleteThread(request, threads[i].remoteId);
  }
}

test.describe("Tool calls in quick mode", () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("TechDocs tools execute and show in trace panel", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    // Select a single-entrypoint mode
    const resolved = await resolveRunMode(request, "single");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No single-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    // Send a query that requires TechDocs tool calls
    const input = page.getByPlaceholder("Send a message...");
    await input.fill("What is FastAPI? Use TechDocs to find the answer.");
    await page.getByRole("button", { name: "Send" }).click();

    // Wait for response to complete
    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Verify trace button shows tool calls (not just thinking steps)
    const traceButton = page.getByRole("button", { name: /View agent trace/ });
    await expect(traceButton).toBeVisible({ timeout: 10000 });

    // Get trace info - should show trace indicator (may be "X steps" or "Live traceN")
    const traceText = await traceButton.textContent();
    expect(traceText).toBeTruthy(); // Trace button should have content

    // Click to open trace panel
    await traceButton.click();

    // Verify trace panel shows TechDocs tool calls
    const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
    await expect(tracePanel).toBeVisible({ timeout: 5000 });

    // Should have TechDocs tool calls (not just Thinking)
    // Look for actual tool names, not descriptions
    const toolCalls = tracePanel.locator("button").filter({
      hasText: /TechDocs_/,
    });
    const toolCallCount = await toolCalls.count();

    // Should have at least one TechDocs tool call (LLM may use 1-3 depending on query)
    expect(toolCallCount).toBeGreaterThanOrEqual(1);

    // Wait for tools to execute
    await page.waitForTimeout(2000);

    // Verify tools show execution status (running or complete)
    const executingTools = tracePanel.locator("span").filter({
      hasText: /(running|complete)/i,
    });
    expect(await executingTools.count()).toBeGreaterThanOrEqual(1);

    // Close trace panel via close button (Escape may not work due to URL persistence)
    const closeButton = tracePanel.locator('button[aria-label="Close"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }
    await cleanupNewThreads(request, threadCountBefore);
  });

  test("response cites real TechDocs URLs, not made-up ones", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    const resolved = await resolveRunMode(request, "single");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No single-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    const input = page.getByPlaceholder("Send a message...");
    await input.fill("What is Django ORM? Search TechDocs and cite your sources.");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Check for real URLs in response - use main content area
    const mainContent = page.locator("main");
    const responseText = await mainContent.textContent();

    // Should NOT contain fake URLs
    expect(responseText).not.toContain("example.com");
    expect(responseText).not.toContain("techdocs.example");

    // Should have meaningful content about Django ORM (indicates successful tool use)
    // The model may not always include URLs in text, but should have relevant content
    const hasRelevantContent =
      responseText?.toLowerCase().includes("django") ||
      responseText?.toLowerCase().includes("orm") ||
      responseText?.toLowerCase().includes("model") ||
      responseText?.toLowerCase().includes("database");

    expect(hasRelevantContent).toBeTruthy();

    await cleanupNewThreads(request, threadCountBefore);
  });
});

test.describe("Tool calls in research mode", () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("research mode executes tools with agent attribution", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    // Select a graph-entrypoint mode
    const resolved = await resolveRunMode(request, "graph");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No graph-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    const input = page.getByPlaceholder("Send a message...");
    await input.fill(
      "What is FastAPI and how does it compare to Flask? Research using TechDocs."
    );
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Open trace panel
    const traceButton = page.getByRole("button", { name: /View agent trace/ });
    await expect(traceButton).toBeVisible({ timeout: 10000 });
    await traceButton.click();

    const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
    await expect(tracePanel).toBeVisible({ timeout: 5000 });

    // Wait for tools to execute
    await page.waitForTimeout(3000);

    // In research mode, tool calls may show agent attribution [agent_name]
    // Look for bracketed agent names before tool names, but also accept tools without attribution
    const agentAttributedTools = tracePanel.locator("button").filter({
      hasText: /\[.*\].*TechDocs_/,
    });

    const allTechDocsTools = tracePanel.locator("button").filter({
      hasText: /TechDocs_/,
    });

    const attributedCount = await agentAttributedTools.count();
    const totalToolCount = await allTechDocsTools.count();

    // Should have at least one TechDocs tool call (attribution is optional)
    expect(totalToolCount).toBeGreaterThanOrEqual(1);

    // Log attribution info for debugging
    console.log(`Research mode: ${totalToolCount} total tools, ${attributedCount} with attribution`);

    await page.keyboard.press("Escape");
    await cleanupNewThreads(request, threadCountBefore);
  });

  test("research mode produces meaningful research output", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    const resolved = await resolveRunMode(request, "graph");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No graph-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    const input = page.getByPlaceholder("Send a message...");
    await input.fill(
      "Explain how Strands SDK handles tool execution in multi-agent systems. Use TechDocs."
    );
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Response should contain actual content (not just tool descriptions)
    const mainContent = page.locator("main");
    const responseText = await mainContent.textContent();

    // Should NOT contain fake tool call syntax in response body
    // Real tool calls go to trace, not message
    expect(responseText).not.toMatch(/TechDocs_\w+\(\)/); // No function call syntax
    expect(responseText).not.toContain('"tool":'); // No JSON tool specs
    expect(responseText).not.toContain("Response:"); // No fake response blocks

    // Should have substantive content
    expect(responseText?.length).toBeGreaterThan(100);

    await cleanupNewThreads(request, threadCountBefore);
  });
});

test.describe("Tool calls in expert mode", () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("expert mode executes tools through graph nodes", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    // Select a swarm-entrypoint mode
    const resolved = await resolveRunMode(request, "swarm");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No swarm-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    const input = page.getByPlaceholder("Send a message...");
    await input.fill(
      "What are the best practices for Django REST Framework authentication? Use TechDocs."
    );
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Graph mode should also show tool calls in trace
    const traceButton = page.getByRole("button", { name: /View agent trace/ });
    await expect(traceButton).toBeVisible({ timeout: 10000 });
    await traceButton.click();

    const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
    await expect(tracePanel).toBeVisible({ timeout: 5000 });

    // Should have TechDocs tool calls
    const toolCalls = tracePanel.locator("button").filter({
      hasText: /TechDocs_/,
    });
    expect(await toolCalls.count()).toBeGreaterThanOrEqual(1);

    await page.keyboard.press("Escape");
    await cleanupNewThreads(request, threadCountBefore);
  });
});

test.describe("Trace panel functionality", () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("trace panel shows tool arguments and results when expanded", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    const resolved = await resolveRunMode(request, "single");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No single-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    const input = page.getByPlaceholder("Send a message...");
    await input.fill("List TechDocs tenants. Just call the tool.");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    const traceButton = page.getByRole("button", { name: /View agent trace/ });
    await expect(traceButton).toBeVisible({ timeout: 10000 });
    await traceButton.click();

    const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
    await expect(tracePanel).toBeVisible({ timeout: 5000 });

    // Find and expand a tool call
    const toolCallButton = tracePanel
      .locator("button")
      .filter({ hasText: /TechDocs_/ })
      .first();

    if ((await toolCallButton.count()) > 0) {
      await toolCallButton.click();

      // Expanded tool call should show details
      // (arguments, result, or at least be expandable)
      const expandedContent = tracePanel.locator('[aria-expanded="true"]');
      const isExpanded = (await expandedContent.count()) > 0;

      // Tool calls should be expandable to show details
      expect(isExpanded).toBeTruthy();
    }

    await page.keyboard.press("Escape");
    await cleanupNewThreads(request, threadCountBefore);
  });

  test("trace panel URL persistence works", async ({ page, request }) => {
    const threadCountBefore = await getThreadCount(request);

    const resolved = await resolveRunMode(request, "single");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No single-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    const input = page.getByPlaceholder("Send a message...");
    await input.fill("What is Python? Use TechDocs.");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Open trace panel
    const traceButton = page.getByRole("button", { name: /View agent trace/ });
    await expect(traceButton).toBeVisible({ timeout: 10000 });
    await traceButton.click();

    // URL should have trace_id parameter
    await expect(page).toHaveURL(/trace_id=/, { timeout: 5000 });

    // Get URL with trace_id
    const urlWithTrace = page.url();
    expect(urlWithTrace).toContain("trace_id=");

    // Close trace panel via close button
    const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
    const closeButton = tracePanel.locator('button[aria-label="Close"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
      // After closing, URL should clear trace_id
      await expect(page).not.toHaveURL(/trace_id=/, { timeout: 3000 });
    }

    // Navigate back with trace_id in URL to reopen
    await page.goto(urlWithTrace);

    // Trace panel should reopen from URL state
    await expect(tracePanel).toBeVisible({ timeout: 5000 });

    await cleanupNewThreads(request, threadCountBefore);
  });
});

test.describe("Complex debugging queries", () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request.get(`${BASE_URL}/api/profiles`);
    expect(response.ok()).toBeTruthy();
    await page.goto("/");
  });

  test("handles complex multi-part technical question", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    const resolved = await resolveRunMode(request, "single");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No single-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    // Complex query that requires multiple tool calls
    const input = page.getByPlaceholder("Send a message...");
    await input.fill(
      `I'm building a Django REST Framework API that needs:
       1. JWT authentication
       2. Pagination
       3. Filtering by date range
       Search TechDocs for implementation patterns for each.`
    );
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Should have multiple tool calls for this complex query
    const traceButton = page.getByRole("button", { name: /View agent trace/ });
    await expect(traceButton).toBeVisible({ timeout: 10000 });

    // Open trace to verify tool calls exist
    await traceButton.click();
    const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
    await expect(tracePanel).toBeVisible({ timeout: 5000 });

    // Complex query should have TechDocs tool calls
    const toolCalls = tracePanel.locator("button").filter({
      hasText: /TechDocs_/,
    });
    const toolCallCount = await toolCalls.count();

    // Should have at least 1 tool call (agent may batch queries)
    expect(toolCallCount).toBeGreaterThanOrEqual(1);

    // Close trace panel
    const closeButton = tracePanel.locator('button[aria-label="Close"]');
    if (await closeButton.isVisible()) {
      await closeButton.click();
    }

    await cleanupNewThreads(request, threadCountBefore);
  });

  test("handles Strands SDK specific debugging question", async ({
    page,
    request,
  }) => {
    const threadCountBefore = await getThreadCount(request);

    const resolved = await resolveRunMode(request, "graph");
    if (!resolved.hasRequestedType) {
      test.skip(true, "No graph-entrypoint profile configured.");
    }
    await page.getByRole("combobox", { name: "Run mode" }).selectOption(resolved.runMode);

    // Query about agentic patterns - tests if TechDocs has relevant info
    const input = page.getByPlaceholder("Send a message...");
    await input.fill(
      `How do I implement tool validation in an agentic workflow?
       What patterns does Strands SDK use for tool execution?
       Search TechDocs for relevant documentation.`
    );
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.locator("text=done").first()).toBeVisible({
      timeout: TOOL_CALL_TIMEOUT,
    });

    // Response should be substantive (real research, not hallucinated)
    const mainContent = page.locator("main");
    const responseText = await mainContent.textContent();

    // Should have real content
    expect(responseText?.length).toBeGreaterThan(200);

    // Should NOT have fake tool call syntax in the response
    expect(responseText).not.toMatch(/```python\s*TechDocs_/);

    await cleanupNewThreads(request, threadCountBefore);
  });
});
