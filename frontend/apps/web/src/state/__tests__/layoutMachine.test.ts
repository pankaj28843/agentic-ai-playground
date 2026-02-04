import { createActor } from "xstate";
import { describe, expect, it } from "vitest";

import { layoutMachine, SIDEBAR_LIMITS, TRACE_LIMITS } from "../layoutMachine";

describe("layoutMachine", () => {
  it("clamps sidebar resize within limits", () => {
    const actor = createActor(layoutMachine, {
      input: { sidebarWidth: SIDEBAR_LIMITS.defaultWidth, traceWidth: TRACE_LIMITS.defaultWidth },
    });
    actor.start();

    actor.send({ type: "SIDEBAR.RESIZE.START", clientX: 100 });
    actor.send({ type: "RESIZE.MOVE", clientX: 1000 });

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.sidebarWidth).toBe(SIDEBAR_LIMITS.max);

    actor.send({ type: "RESIZE.MOVE", clientX: -1000 });
    expect(actor.getSnapshot().context.sidebarWidth).toBe(SIDEBAR_LIMITS.min);
  });

  it("clamps trace resize within limits", () => {
    const actor = createActor(layoutMachine, {
      input: { sidebarWidth: SIDEBAR_LIMITS.defaultWidth, traceWidth: TRACE_LIMITS.defaultWidth },
    });
    actor.start();

    actor.send({ type: "TRACE.RESIZE.START", clientX: 200 });
    actor.send({ type: "RESIZE.MOVE", clientX: -1000 });
    expect(actor.getSnapshot().context.traceWidth).toBe(TRACE_LIMITS.max);

    actor.send({ type: "RESIZE.MOVE", clientX: 2000 });
    expect(actor.getSnapshot().context.traceWidth).toBe(TRACE_LIMITS.min);
  });
});
