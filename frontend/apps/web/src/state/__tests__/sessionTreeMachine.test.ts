import { createActor } from "xstate";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, SessionTreeResponse } from "@agentic-ai-playground/api-client";
import { sessionTreeMachine } from "../sessionTreeMachine";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

describe("sessionTreeMachine", () => {
  it("loads tree for thread", async () => {
    const tree: SessionTreeResponse = {
      sessionId: "session-1",
      header: { id: "entry-1", timestamp: "" },
      entries: [{ id: "entry-1", label: null, type: "message", timestamp: "" }],
      roots: ["entry-1"],
      children: {},
    };
    const apiClient = {
      getSessionTree: vi.fn().mockResolvedValue(tree),
      labelSessionEntry: vi.fn(),
    } as unknown as ApiClient;
    const actor = createActor(sessionTreeMachine, { input: { apiClient } });
    actor.start();

    actor.send({ type: "THREAD.SET", threadId: "thread-1" });
    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.tree?.sessionId).toBe("session-1");
    expect(snapshot.context.entriesById["entry-1"]).toBeDefined();
    expect(snapshot.context.labelDraft).toBe("");
  });

  it("handles tree errors", async () => {
    const apiClient = {
      getSessionTree: vi.fn().mockRejectedValue(new Error("boom")),
      labelSessionEntry: vi.fn(),
    } as unknown as ApiClient;
    const actor = createActor(sessionTreeMachine, { input: { apiClient } });
    actor.start();

    actor.send({ type: "THREAD.SET", threadId: "thread-1" });
    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.error).toBe("boom");
  });

  it("labels entry and refreshes", async () => {
    const tree: SessionTreeResponse = {
      sessionId: "session-1",
      header: { id: "entry-1", timestamp: "" },
      entries: [{ id: "entry-1", label: null, type: "message", timestamp: "" }],
      roots: ["entry-1"],
      children: {},
    };
    const apiClient = {
      getSessionTree: vi.fn().mockResolvedValue(tree),
      labelSessionEntry: vi.fn().mockResolvedValue(undefined),
    } as unknown as ApiClient;
    const actor = createActor(sessionTreeMachine, { input: { apiClient } });
    actor.start();

    actor.send({ type: "THREAD.SET", threadId: "thread-1" });
    await flushPromises();

    actor.send({ type: "ENTRY.LABEL", entryId: "entry-1", label: "Label" });
    await flushPromises();

    expect(apiClient.labelSessionEntry).toHaveBeenCalledWith(
      "thread-1",
      "entry-1",
      "Label",
    );
  });

  it("tracks label draft changes", async () => {
    const tree: SessionTreeResponse = {
      sessionId: "session-1",
      header: { id: "entry-1", timestamp: "" },
      entries: [{ id: "entry-1", label: "Initial", type: "message", timestamp: "" }],
      roots: ["entry-1"],
      children: {},
    };
    const apiClient = {
      getSessionTree: vi.fn().mockResolvedValue(tree),
      labelSessionEntry: vi.fn(),
    } as unknown as ApiClient;
    const actor = createActor(sessionTreeMachine, { input: { apiClient } });
    actor.start();

    actor.send({ type: "THREAD.SET", threadId: "thread-1" });
    await flushPromises();

    actor.send({ type: "ENTRY.SET_ACTIVE", entryId: "entry-1" });
    expect(actor.getSnapshot().context.labelDraft).toBe("Initial");

    actor.send({ type: "ENTRY.LABEL.DRAFT.SET", value: "Edited" });
    expect(actor.getSnapshot().context.labelDraft).toBe("Edited");
  });

  it("refresh keeps active entry draft in sync", async () => {
    const tree1: SessionTreeResponse = {
      sessionId: "session-1",
      header: { id: "entry-1", timestamp: "" },
      entries: [{ id: "entry-1", label: "First", type: "message", timestamp: "" }],
      roots: ["entry-1"],
      children: {},
      leafId: "entry-1",
    };
    const tree2: SessionTreeResponse = {
      sessionId: "session-1",
      header: { id: "entry-1", timestamp: "" },
      entries: [{ id: "entry-1", label: "Updated", type: "message", timestamp: "" }],
      roots: ["entry-1"],
      children: {},
      leafId: "entry-1",
    };
    const apiClient = {
      getSessionTree: vi.fn().mockResolvedValueOnce(tree1).mockResolvedValueOnce(tree2),
      labelSessionEntry: vi.fn(),
    } as unknown as ApiClient;
    const actor = createActor(sessionTreeMachine, { input: { apiClient } });
    actor.start();

    actor.send({ type: "THREAD.SET", threadId: "thread-1" });
    await flushPromises();

    actor.send({ type: "ENTRY.SET_ACTIVE", entryId: "entry-1" });
    actor.send({ type: "TREE.REFRESH" });
    await flushPromises();

    expect(actor.getSnapshot().context.labelDraft).toBe("Updated");
  });
});
