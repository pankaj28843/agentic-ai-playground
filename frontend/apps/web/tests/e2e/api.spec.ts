import { expect, test, APIRequestContext } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL;
if (!BASE_URL) {
  throw new Error("E2E_BASE_URL is required for e2e tests.");
}

// Helper to delete a thread by ID
async function deleteThread(request: APIRequestContext, threadId: string) {
  try {
    await request.delete(`${BASE_URL}/api/threads/${threadId}`);
  } catch {
    // Ignore cleanup errors
  }
}

test.describe("API endpoints", () => {
  test("GET /api/profiles returns valid profiles and modes", async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/profiles`);

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();

    // Verify response structure
    expect(data).toHaveProperty("profiles");
    expect(data).toHaveProperty("runModes");
    expect(Array.isArray(data.profiles)).toBeTruthy();
    expect(Array.isArray(data.runModes)).toBeTruthy();

    // Verify at least one profile exists
    expect(data.profiles.length).toBeGreaterThan(0);

    // Verify profile structure
    const profile = data.profiles[0];
    expect(profile).toHaveProperty("id");
    expect(profile).toHaveProperty("name");
    expect(profile).toHaveProperty("description");

    // Run modes should include the profile ids
    const profileIds = data.profiles.map((item: { id: string }) => item.id);
    for (const id of profileIds) {
      expect(data.runModes).toContain(id);
    }

    if (data.defaultRunMode) {
      expect(data.runModes).toContain(data.defaultRunMode);
    }
  });

  test("GET /api/threads returns thread list", async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/threads`);

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty("threads");
    expect(Array.isArray(data.threads)).toBeTruthy();
  });

  test("POST /api/threads creates new thread", async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/threads`, {
      data: {},
    });

    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const data = await response.json();
    // API returns remoteId not id
    expect(data).toHaveProperty("remoteId");
    expect(typeof data.remoteId).toBe("string");
    expect(data.remoteId.length).toBeGreaterThan(0);

    // Cleanup: Delete the thread we just created
    await deleteThread(request, data.remoteId);
  });

  test("POST /api/chat/run streams response in single mode", async ({ request }) => {
    // First create a thread
    const threadResponse = await request.post(`${BASE_URL}/api/threads`);
    const thread = await threadResponse.json();

    // Fetch run modes to pick a valid profile
    const profilesResponse = await request.get(`${BASE_URL}/api/profiles`);
    const profilesData = await profilesResponse.json();
    const runMode = profilesData.defaultRunMode ?? profilesData.runModes[0];

    // Then send a chat message
    const chatResponse = await request.post(`${BASE_URL}/api/chat/run`, {
      data: {
        messages: [
          {
            id: "test-msg-1",
            role: "user",
            content: [{ type: "text", text: "Reply with exactly: OK" }],
            createdAt: new Date().toISOString(),
          },
        ],
        threadId: thread.remoteId,
        runMode,
      },
    });

    expect(chatResponse.ok()).toBeTruthy();
    expect(chatResponse.status()).toBe(200);

    // Response should be JSONL stream
    const contentType = chatResponse.headers()["content-type"];
    expect(contentType).toContain("application/jsonl");

    // Read streaming response
    const body = await chatResponse.text();
    expect(body.length).toBeGreaterThan(0);

    // Each line should be valid JSON
    const lines = body.trim().split("\n").filter(Boolean);
    expect(lines.length).toBeGreaterThan(0);

    for (const line of lines) {
      const parsed = JSON.parse(line);
      // Response uses rich content format
      expect("content" in parsed && Array.isArray(parsed.content)).toBeTruthy();
    }

    // Cleanup: Delete the thread we created
    await deleteThread(request, thread.remoteId);
  });
});
