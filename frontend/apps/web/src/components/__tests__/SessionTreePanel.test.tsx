import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SessionTreePanel } from "../SessionTreePanel";

const composerApi = {
  setText: vi.fn(),
};

vi.mock("@assistant-ui/react", () => {
  return {
    useAssistantApi: () => ({ composer: () => composerApi }),
  };
});

type MockSessionTree = {
  threadId: string | null;
  tree: {
    sessionId: string;
    header: { id: string; timestamp: string };
    entries: Array<{ id: string; type: string; timestamp: string; messagePreview?: string; summary?: string; label?: string | null }>;
    roots: string[];
    children: Record<string, string[]>;
    leafId?: string;
  } | null;
  entriesById: Record<string, { id: string; type: string; timestamp: string; messagePreview?: string; summary?: string; label?: string | null }>;
  activeEntryId: string | null;
  labelDraft: string;
  setActiveEntryId: (entryId: string | null) => void;
  setLabelDraft: (value: string) => void;
  refresh: () => void;
  labelEntry: (entryId: string, label: string | null) => void;
  isLoading: boolean;
  error: string | null;
};

let mockSessionTree: MockSessionTree;

vi.mock("../../contexts/SessionTreeContext", () => {
  return {
    useSessionTree: () => mockSessionTree,
  };
});

describe("SessionTreePanel", () => {
  afterEach(() => {
    cleanup();
  });
  it("renders entries and allows summary insertion", () => {
    const setActiveEntryId = vi.fn();
    mockSessionTree = {
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
      labelDraft: "",
      setActiveEntryId,
      setLabelDraft: vi.fn(),
      refresh: vi.fn(),
      labelEntry: vi.fn(),
      isLoading: false,
      error: null,
    };

    render(<SessionTreePanel />);
    expect(screen.getByText("Branch summary")).toBeInTheDocument();
    const insert = screen.getByRole("button", { name: /insert summary/i });
    fireEvent.click(insert);
    expect(composerApi.setText).toHaveBeenCalledWith("Branch summary");

    fireEvent.click(screen.getByRole("button", { name: /branch summary/i }));
    expect(setActiveEntryId).toHaveBeenCalledWith("entry-1");
  });

  it("shows empty state and loading/error hints", () => {
    const refresh = vi.fn();
    mockSessionTree = {
      threadId: null,
      tree: null,
      entriesById: {},
      activeEntryId: null,
      labelDraft: "",
      setActiveEntryId: vi.fn(),
      setLabelDraft: vi.fn(),
      refresh,
      labelEntry: vi.fn(),
      isLoading: false,
      error: null,
    };

    const { rerender } = render(<SessionTreePanel />);
    expect(screen.getByText(/start a thread/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
    expect(refresh).toHaveBeenCalled();

    mockSessionTree = {
      ...mockSessionTree,
      threadId: "thread-1",
      isLoading: true,
    };
    rerender(<SessionTreePanel />);
    expect(screen.getByText(/loading tree/i)).toBeInTheDocument();

    mockSessionTree = {
      ...mockSessionTree,
      isLoading: false,
      error: "boom",
    };
    rerender(<SessionTreePanel />);
    expect(screen.getByText("boom")).toBeInTheDocument();
  });

  it("shows active entry panel and saves label", () => {
    const labelEntry = vi.fn();
    const setLabelDraft = vi.fn();
    mockSessionTree = {
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
        },
      },
      activeEntryId: "entry-1",
      labelDraft: "Draft",
      setActiveEntryId: vi.fn(),
      setLabelDraft,
      refresh: vi.fn(),
      labelEntry,
      isLoading: false,
      error: null,
    };

    render(<SessionTreePanel />);

    const input = screen.getByPlaceholderText(/checkpoint name/i);
    fireEvent.change(input, { target: { value: "Next" } });
    expect(setLabelDraft).toHaveBeenCalledWith("Next");

    fireEvent.click(screen.getByRole("button", { name: /save label/i }));
    expect(labelEntry).toHaveBeenCalledWith("entry-1", "Draft");
  });

  it("renders empty tree hint", () => {
    mockSessionTree = {
      threadId: "thread-1",
      tree: {
        sessionId: "sess",
        header: { id: "sess", timestamp: "now" },
        entries: [],
        roots: [],
        children: {},
        leafId: undefined,
      },
      entriesById: {},
      activeEntryId: null,
      labelDraft: "",
      setActiveEntryId: vi.fn(),
      setLabelDraft: vi.fn(),
      refresh: vi.fn(),
      labelEntry: vi.fn(),
      isLoading: false,
      error: null,
    };

    render(<SessionTreePanel />);
    expect(screen.getByText(/no entries yet/i)).toBeInTheDocument();
  });

  it("prefers label over summary and preview", () => {
    mockSessionTree = {
      threadId: "thread-1",
      tree: {
        sessionId: "sess",
        header: { id: "sess", timestamp: "now" },
        entries: [
          {
            id: "entry-1",
            type: "message",
            timestamp: "now",
            label: "Labeled",
            summary: "Summary",
            messagePreview: "Preview",
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
          label: "Labeled",
          summary: "Summary",
          messagePreview: "Preview",
        },
      },
      activeEntryId: null,
      labelDraft: "",
      setActiveEntryId: vi.fn(),
      setLabelDraft: vi.fn(),
      refresh: vi.fn(),
      labelEntry: vi.fn(),
      isLoading: false,
      error: null,
    };

    render(<SessionTreePanel />);
    expect(screen.getByText("Labeled")).toBeInTheDocument();
  });

  it("falls back to preview or untitled title", () => {
    mockSessionTree = {
      threadId: "thread-1",
      tree: {
        sessionId: "sess",
        header: { id: "sess", timestamp: "now" },
        entries: [
          {
            id: "entry-1",
            type: "message",
            timestamp: "now",
            messagePreview: "Preview",
          },
          {
            id: "entry-2",
            type: "message",
            timestamp: "now",
          },
        ],
        roots: ["entry-1", "entry-2"],
        children: {},
        leafId: "entry-1",
      },
      entriesById: {
        "entry-1": {
          id: "entry-1",
          type: "message",
          timestamp: "now",
          messagePreview: "Preview",
        },
        "entry-2": {
          id: "entry-2",
          type: "message",
          timestamp: "now",
        },
      },
      activeEntryId: null,
      labelDraft: "",
      setActiveEntryId: vi.fn(),
      setLabelDraft: vi.fn(),
      refresh: vi.fn(),
      labelEntry: vi.fn(),
      isLoading: false,
      error: null,
    };

    render(<SessionTreePanel />);
    expect(screen.getByText("Preview")).toBeInTheDocument();
    expect(screen.getByText("Untitled entry")).toBeInTheDocument();
  });
});
