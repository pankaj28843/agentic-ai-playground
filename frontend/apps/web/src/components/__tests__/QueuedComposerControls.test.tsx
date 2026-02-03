import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { QueuedComposerControls } from "../QueuedComposerControls";

type MockState = {
  thread: { isRunning: boolean };
  composer: { text: string; attachments: unknown[] };
};

let mockState: MockState;

const composerApi = {
  reset: vi.fn(),
  setText: vi.fn(),
  send: vi.fn(),
};

const threadApi = {
  cancelRun: vi.fn(),
};

const api = {
  composer: () => composerApi,
  thread: () => threadApi,
};

vi.mock("@assistant-ui/react", () => {
  return {
    useAssistantApi: () => api,
    useAssistantState: (selector: (state: MockState) => unknown) => selector(mockState),
    ComposerPrimitive: {
      Send: ({ children }: { children: ReactNode }) => <>{children}</>,
      Cancel: ({ children }: { children: ReactNode }) => <>{children}</>,
    },
  };
});

describe("QueuedComposerControls", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    mockState = {
      thread: { isRunning: false },
      composer: { text: "", attachments: [] },
    };
    composerApi.reset.mockReset();
    composerApi.setText.mockReset();
    composerApi.send.mockReset();
    threadApi.cancelRun.mockReset();
  });

  it("shows the send button when idle", () => {
    render(<QueuedComposerControls />);

    expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /steer/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /follow-up/i })).not.toBeInTheDocument();
  });

  it("queues a follow-up and sends it after the run ends", async () => {
    mockState = {
      thread: { isRunning: true },
      composer: { text: "Next steps", attachments: [] },
    };

    const { rerender } = render(<QueuedComposerControls />);

    fireEvent.click(screen.getByRole("button", { name: /follow-up/i }));

    expect(composerApi.reset).toHaveBeenCalled();
    expect(threadApi.cancelRun).not.toHaveBeenCalled();
    expect(screen.getByText(/1 queued/i)).toBeInTheDocument();

    mockState = {
      thread: { isRunning: false },
      composer: { text: "", attachments: [] },
    };
    rerender(<QueuedComposerControls />);

    await waitFor(() => {
      expect(composerApi.setText).toHaveBeenCalledWith("Next steps");
      expect(composerApi.send).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.queryByText(/1 queued/i)).not.toBeInTheDocument();
    });
  });

  it("steers the active run and queues the message", () => {
    mockState = {
      thread: { isRunning: true },
      composer: { text: "Change direction", attachments: [] },
    };

    render(<QueuedComposerControls />);

    fireEvent.click(screen.getByRole("button", { name: /steer/i }));

    expect(composerApi.reset).toHaveBeenCalled();
    expect(threadApi.cancelRun).toHaveBeenCalled();
    expect(screen.getByText(/1 queued/i)).toBeInTheDocument();
  });

  it("warns when attachments are present and does not queue", () => {
    mockState = {
      thread: { isRunning: true },
      composer: { text: "With attachment", attachments: [{ name: "file.txt" }] },
    };

    render(<QueuedComposerControls />);

    fireEvent.click(screen.getByRole("button", { name: /follow-up/i }));

    expect(screen.getByText(/attachments cannot be queued yet/i)).toBeInTheDocument();
    expect(composerApi.reset).not.toHaveBeenCalled();
    expect(threadApi.cancelRun).not.toHaveBeenCalled();
    expect(screen.queryByText(/1 queued/i)).not.toBeInTheDocument();
  });
});
