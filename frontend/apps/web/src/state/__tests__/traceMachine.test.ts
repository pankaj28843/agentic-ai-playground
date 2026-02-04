import { createActor } from "xstate";
import { describe, expect, it } from "vitest";

import { traceMachine } from "../traceMachine";

const storageKey = (messageId: string) => `playground-trace-expanded:${messageId}`;

describe("traceMachine", () => {
  it("loads expanded items on open and toggles", () => {
    localStorage.setItem(storageKey("msg-1"), JSON.stringify([1]));

    const actor = createActor(traceMachine, { input: { initialTraceId: null } });
    actor.start();

    actor.send({
      type: "TRACE.OPEN",
      items: [],
      status: "running",
      messageId: "msg-1",
    });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.expandedItems.has(1)).toBe(true);

    actor.send({ type: "TRACE.TOGGLE_EXPANDED", index: 2 });
    expect(actor.getSnapshot().context.expandedItems.has(2)).toBe(true);

    const stored = JSON.parse(localStorage.getItem(storageKey("msg-1")) ?? "[]");
    expect(stored).toContain(2);
  });

  it("clears expanded items on close", () => {
    localStorage.setItem(storageKey("msg-2"), JSON.stringify([0]));

    const actor = createActor(traceMachine, { input: { initialTraceId: null } });
    actor.start();
    actor.send({
      type: "TRACE.OPEN",
      items: [],
      status: "running",
      messageId: "msg-2",
    });

    actor.send({ type: "TRACE.CLOSE" });

    expect(localStorage.getItem(storageKey("msg-2"))).toBeNull();
    expect(actor.getSnapshot().context.expandedItems.size).toBe(0);
  });

  it("tracks full output toggles per session", () => {
    const actor = createActor(traceMachine, { input: { initialTraceId: null } });
    actor.start();

    actor.send({
      type: "TRACE.OPEN",
      items: [],
      status: "running",
      messageId: "msg-4",
    });

    actor.send({ type: "TRACE.TOGGLE_FULL_OUTPUT", index: 1 });
    expect(actor.getSnapshot().context.fullOutputItems.has(1)).toBe(true);

    actor.send({ type: "TRACE.CLOSE" });
    expect(actor.getSnapshot().context.fullOutputItems.size).toBe(0);
  });

  it("updates phoenix and runtime metadata", () => {
    const actor = createActor(traceMachine, { input: { initialTraceId: null } });
    actor.start();

    actor.send({
      type: "TRACE.OPEN",
      items: [],
      status: "running",
      messageId: "msg-3",
    });
    actor.send({ type: "PHOENIX.METADATA", metadata: { traceId: "t1", sessionId: "s1" } });
    actor.send({ type: "RUNTIME.METADATA", metadata: { runMode: "quick", profileName: "general" } });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.trace.phoenix?.traceId).toBe("t1");
    expect(snapshot.context.trace.runtime?.runMode).toBe("quick");
  });
});
