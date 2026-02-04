import { createActor } from "xstate";
import { describe, expect, it } from "vitest";

import type { ResourcesResponse } from "@agentic-ai-playground/api-client";
import { composerQueueMachine } from "../composerQueueMachine";

const resources: ResourcesResponse = {
  skills: [
    { name: "review", description: "", content: "Do review", source: "" },
  ],
  prompts: [
    { name: "summarize", description: "", content: "Summarize", source: "" },
  ],
  diagnostics: { warnings: [] },
};

describe("composerQueueMachine", () => {
  it("warns when attachments are queued", () => {
    const actor = createActor(composerQueueMachine, { input: {} });
    actor.start();

    actor.send({
      type: "QUEUE.REQUEST",
      mode: "follow-up",
      composerText: "Test",
      attachmentCount: 1,
      resources,
      enabledSkills: [],
      enabledPrompts: [],
    });

    expect(actor.getSnapshot().context.warning).toBe("Attachments cannot be queued yet.");
  });

  it("queues steer message and requests cancel/reset", () => {
    const actor = createActor(composerQueueMachine, { input: {} });
    actor.start();

    actor.send({
      type: "QUEUE.REQUEST",
      mode: "steer",
      composerText: "Hello",
      attachmentCount: 0,
      resources,
      enabledSkills: [],
      enabledPrompts: [],
    });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.queue).toHaveLength(1);
    expect(snapshot.context.pendingReset).toBe(true);
    expect(snapshot.context.cancelRequested).toBe(true);
  });

  it("dequeues when run completes", () => {
    const actor = createActor(composerQueueMachine, { input: {} });
    actor.start();

    actor.send({
      type: "QUEUE.REQUEST",
      mode: "follow-up",
      composerText: "Hello",
      attachmentCount: 0,
      resources,
      enabledSkills: [],
      enabledPrompts: [],
    });

    actor.send({ type: "ASSISTANT.RUNNING.CHANGED", isRunning: true });
    actor.send({ type: "ASSISTANT.RUNNING.CHANGED", isRunning: false });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.pendingSend?.text).toBe("Hello");
    expect(snapshot.context.queue).toHaveLength(0);
  });

  it("prepares immediate sends", () => {
    const actor = createActor(composerQueueMachine, { input: {} });
    actor.start();

    actor.send({
      type: "SEND.REQUEST",
      composerText: "Send now",
      attachmentCount: 0,
      resources,
      enabledSkills: [],
      enabledPrompts: [],
    });

    expect(actor.getSnapshot().context.pendingSend?.text).toBe("Send now");
  });

  it("ignores empty send requests", () => {
    const actor = createActor(composerQueueMachine, { input: {} });
    actor.start();

    actor.send({
      type: "SEND.REQUEST",
      composerText: "",
      attachmentCount: 0,
      resources,
      enabledSkills: [],
      enabledPrompts: [],
    });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.pendingSend).toBeNull();
    expect(snapshot.context.warning).toBeNull();
  });
});
