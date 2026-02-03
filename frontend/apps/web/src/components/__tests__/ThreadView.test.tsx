import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ThreadView } from "../ThreadView";

vi.mock("../QueuedComposerControls", () => {
  return {
    QueuedComposerControls: () => <div data-testid="queued-controls" />,
  };
});

const mockState = {
  composer: { text: "" },
};

const api = {
  composer: () => ({ setText: vi.fn() }),
};

vi.mock("@assistant-ui/react", () => {
  const wrap = ({ children }: { children: ReactNode }) => <>{children}</>;
  return {
    ActionBarPrimitive: {
      Root: wrap,
      Copy: wrap,
      Reload: wrap,
      Edit: wrap,
    },
    AttachmentPrimitive: {
      Root: wrap,
      Remove: wrap,
      Name: wrap,
      Delete: wrap,
    },
    AuiIf: ({
      children,
      condition,
    }: {
      children: ReactNode;
      condition: (state: { thread: { isEmpty: boolean } }) => boolean;
    }) => (condition({ thread: { isEmpty: true } }) ? <>{children}</> : null),
    ComposerPrimitive: {
      Root: wrap,
      AttachmentDropzone: wrap,
      Input: ({ placeholder }: { placeholder?: string }) => <textarea placeholder={placeholder} />,
      AddAttachment: wrap,
      Attachments: () => null,
      Cancel: wrap,
      Send: wrap,
    },
    ErrorPrimitive: {
      Root: wrap,
      Message: () => null,
    },
    MessagePrimitive: {
      Root: wrap,
      Parts: () => null,
      Attachments: () => null,
      If: ({ children }: { children: ReactNode }) => <>{children}</>,
      Error: wrap,
    },
    ThreadPrimitive: {
      Root: wrap,
      Viewport: wrap,
      ViewportFooter: wrap,
      Messages: () => null,
      ScrollToBottom: wrap,
    },
    useAssistantApi: () => api,
    useAssistantState: (selector: (state: typeof mockState) => unknown) => selector(mockState),
    useMessage: () => null,
  };
});

describe("ThreadView", () => {
  it("renders queued composer controls in the composer actions", () => {
    render(<ThreadView />);

    expect(screen.getByTestId("queued-controls")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/send a message/i)).toBeInTheDocument();
  });
});
