import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { SessionTreeResponse } from "@agentic-ai-playground/api-client";
import { SessionTreeProvider, useSessionTree } from "../SessionTreeContext";

const threadListState = {
  mainThreadId: "thread-1",
  threadItems: {
    "thread-1": { remoteId: "remote-1" },
  },
};

const getSessionTreeMock = vi.fn();

vi.mock("@assistant-ui/react", () => ({
  useThreadList: (selector: (state: typeof threadListState) => unknown) => selector(threadListState),
}));

const setActiveSessionBranch = vi.fn();

vi.mock("@agentic-ai-playground/assistant-runtime", () => ({
  setActiveSessionBranch: (...args: unknown[]) => setActiveSessionBranch(...args),
}));

vi.mock("@agentic-ai-playground/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@agentic-ai-playground/api-client")>();
  return {
    ...actual,
    ApiClient: class {
      getSessionTree = getSessionTreeMock;
      labelSessionEntry = vi.fn().mockResolvedValue(undefined);
      constructor() {
        return this;
      }
    },
  };
});

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const SessionTreeProbe = () => {
  const { threadId, activeEntryId, labelDraft, setActiveEntryId, setLabelDraft } = useSessionTree();
  return (
    <div>
      <div data-testid="thread">{threadId ?? "none"}</div>
      <div data-testid="active">{activeEntryId ?? "none"}</div>
      <div data-testid="label">{labelDraft}</div>
      <button type="button" onClick={() => setActiveEntryId("entry-1")}>
        set
      </button>
      <button type="button" onClick={() => setLabelDraft("Draft")}>
        draft
      </button>
    </div>
  );
};

describe("SessionTreeContext", () => {
  it("loads tree and updates active branch", async () => {
    const tree: SessionTreeResponse = {
      sessionId: "session-1",
      header: {
        id: "entry-1",
        timestamp: "",
      },
      entries: [{ id: "entry-1", label: null, type: "message", timestamp: "" }],
      roots: ["entry-1"],
      children: {},
    };
    getSessionTreeMock.mockResolvedValueOnce(tree);

    render(
      <SessionTreeProvider>
        <SessionTreeProbe />
      </SessionTreeProvider>,
    );

    await flushPromises();

    expect(screen.getByTestId("thread").textContent).toBe("remote-1");
    screen.getByText("set").click();
    await waitFor(() => {
      expect(setActiveSessionBranch).toHaveBeenLastCalledWith({
        threadId: "remote-1",
        entryId: "entry-1",
      });
    });
    screen.getByText("draft").click();
    await waitFor(() => {
      expect(screen.getByTestId("label").textContent).toBe("Draft");
    });
  });
});
