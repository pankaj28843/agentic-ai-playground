import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SessionTreePanel } from "../SessionTreePanel";

const composerApi = {
  setText: vi.fn(),
};

vi.mock("@assistant-ui/react", () => {
  return {
    useAssistantApi: () => ({ composer: () => composerApi }),
  };
});

vi.mock("../../contexts/SessionTreeContext", () => {
  return {
    useSessionTree: () => ({
      threadId: "thread-1",
      tree: {
        sessionId: "sess",
        header: { id: "sess", timestamp: "now" },
        entries: [
          {
            id: "entry-1",
            type: "message",
            timestamp: "now",
            messagePreview: "Hello world",
            summary: "Branch summary",
          },
        ],
        roots: ["entry-1"],
        children: {},
        leafId: "entry-1",
      },
      entriesById: {
        "entry-1": {
          id: "entry-1",
          type: "message",
          timestamp: "now",
          messagePreview: "Hello world",
          summary: "Branch summary",
        },
      },
      activeEntryId: null,
      setActiveEntryId: vi.fn(),
      refresh: vi.fn(),
      labelEntry: vi.fn(),
      isLoading: false,
      error: null,
    }),
  };
});

describe("SessionTreePanel", () => {
  it("renders entries and allows summary insertion", () => {
    render(<SessionTreePanel />);
    expect(screen.getByText("Branch summary")).toBeInTheDocument();
    const insert = screen.getByRole("button", { name: /insert summary/i });
    fireEvent.click(insert);
    expect(composerApi.setText).toHaveBeenCalledWith("Branch summary");
  });
});
