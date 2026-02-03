import { describe, expect, it, vi } from "vitest";

import { getActiveSessionBranch, setActiveSessionBranch, subscribeSessionBranch } from "../session-branch";

describe("session branch state", () => {
  it("updates and notifies listeners", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeSessionBranch(listener);

    setActiveSessionBranch({ threadId: "thread-1", entryId: "entry-1" });
    expect(getActiveSessionBranch()).toEqual({ threadId: "thread-1", entryId: "entry-1" });
    expect(listener).toHaveBeenCalledWith({ threadId: "thread-1", entryId: "entry-1" });

    unsubscribe();
    setActiveSessionBranch(null);
    expect(getActiveSessionBranch()).toBeNull();
  });
});
