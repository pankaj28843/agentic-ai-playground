import { createActor } from "xstate";
import { describe, expect, it } from "vitest";

import { appShellMachine } from "../appShellMachine";

describe("appShellMachine", () => {
  it("toggles menu", () => {
    const actor = createActor(appShellMachine, { input: { menuOpen: false } });
    actor.start();

    actor.send({ type: "MENU.TOGGLE" });
    expect(actor.getSnapshot().context.menuOpen).toBe(true);

    actor.send({ type: "MENU.OPEN" });
    expect(actor.getSnapshot().context.menuOpen).toBe(true);

    actor.send({ type: "MENU.CLOSE" });
    expect(actor.getSnapshot().context.menuOpen).toBe(false);
  });

  it("flags trace close when conversation changes", () => {
    const actor = createActor(appShellMachine, { input: { conversationId: null } });
    actor.start();

    actor.send({ type: "ROUTE.CONVERSATION.SET", value: "thread-1" });
    expect(actor.getSnapshot().context.shouldCloseTrace).toBe(false);

    actor.send({ type: "ROUTE.CONVERSATION.SET", value: "thread-2" });
    expect(actor.getSnapshot().context.shouldCloseTrace).toBe(true);

    actor.send({ type: "TRACE.CLOSE.ACK" });
    expect(actor.getSnapshot().context.shouldCloseTrace).toBe(false);
  });
});
