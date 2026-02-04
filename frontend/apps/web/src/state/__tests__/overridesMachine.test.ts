import { createActor } from "xstate";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient, ThreadDetail } from "@agentic-ai-playground/api-client";
import { overridesMachine, readStoredOverrides } from "../overridesMachine";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

describe("overridesMachine", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("hydrates from stored overrides", () => {
    localStorage.setItem(
      "playground-run-overrides-v1",
      JSON.stringify({ modelOverride: "model-a", toolGroupsOverride: ["tools"] }),
    );
    const apiClient = { getThread: vi.fn() } as unknown as ApiClient;
    const actor = createActor(overridesMachine, {
      input: { apiClient, storedOverrides: readStoredOverrides() },
    });
    actor.start();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.modelOverride).toBe("model-a");
    expect(snapshot.context.toolGroupsOverride).toEqual(["tools"]);
  });

  it("merges thread overrides with stored fallback", async () => {
    localStorage.setItem(
      "playground-run-overrides-v1",
      JSON.stringify({ modelOverride: "fallback", toolGroupsOverride: ["stored"] }),
    );
    const thread: ThreadDetail = {
      remoteId: "thread-1",
      status: "regular",
      createdAt: "",
      updatedAt: "",
      modelOverride: null,
      toolGroupsOverride: ["thread-tools"],
    };
    const apiClient = {
      getThread: vi.fn().mockResolvedValue(thread),
    } as unknown as ApiClient;

    const actor = createActor(overridesMachine, {
      input: { apiClient, storedOverrides: readStoredOverrides() },
    });
    actor.start();
    actor.send({ type: "THREAD.SET", threadId: "thread-1" });

    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.modelOverride).toBe("fallback");
    expect(snapshot.context.toolGroupsOverride).toEqual(["thread-tools"]);
  });

  it("persists model override updates", () => {
    const apiClient = { getThread: vi.fn() } as unknown as ApiClient;
    const actor = createActor(overridesMachine, {
      input: { apiClient, storedOverrides: { modelOverride: null, toolGroupsOverride: null } },
    });
    actor.start();
    actor.send({ type: "OVERRIDE.MODEL.SET", value: "model-x" });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.modelOverride).toBe("model-x");

    const stored = JSON.parse(
      localStorage.getItem("playground-run-overrides-v1") ?? "{}",
    );
    expect(stored.modelOverride).toBe("model-x");
  });

  it("persists tool override updates", () => {
    const apiClient = { getThread: vi.fn() } as unknown as ApiClient;
    const actor = createActor(overridesMachine, {
      input: { apiClient, storedOverrides: { modelOverride: null, toolGroupsOverride: null } },
    });
    actor.start();
    actor.send({ type: "OVERRIDE.TOOLGROUPS.SET", value: ["tg"] });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.toolGroupsOverride).toEqual(["tg"]);

    const stored = JSON.parse(
      localStorage.getItem("playground-run-overrides-v1") ?? "{}",
    );
    expect(stored.toolGroupsOverride).toEqual(["tg"]);
  });
});
