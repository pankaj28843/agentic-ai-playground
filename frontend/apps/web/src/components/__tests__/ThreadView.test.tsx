import { render, screen } from "@testing-library/react";
import type { ReactNode, ComponentType } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@agentic-ai-playground/api-client";
import { AppDataProvider } from "../../state/appDataContext";
import { TraceProvider } from "../../contexts/TraceContext";
import { ThreadView } from "../ThreadView";
import { BrowserRouter } from "react-router-dom";

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

let mockMessage: {
  id?: string;
  status?: { type?: string };
  content?: Array<Record<string, unknown>>;
  metadata?: Record<string, unknown>;
} | null = null;

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
      Messages: ({ components }: { components: { AssistantMessage: ComponentType } }) => (
        <components.AssistantMessage />
      ),
      ScrollToBottom: wrap,
    },
    useAssistantApi: () => api,
    useAssistantState: (selector: (state: typeof mockState) => unknown) => selector(mockState),
    useMessage: () => mockMessage,
  };
});

describe("ThreadView", () => {
  afterEach(() => {
    mockMessage = null;
  });

  it("renders queued composer controls in the composer actions", () => {
    mockMessage = null;
    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue({
        profiles: [],
        runModes: [],
        defaultRunMode: null,
      }),
      getSettings: vi.fn().mockResolvedValue({
        models: [],
        defaultModel: null,
        toolGroups: [],
        profileDefaults: [],
        inferenceProfiles: [],
        warnings: [],
      }),
      listResources: vi.fn().mockResolvedValue({
        skills: [],
        prompts: [],
        diagnostics: { warnings: [] },
      }),
      getPhoenixConfig: vi.fn().mockResolvedValue({ enabled: false }),
    } as unknown as ApiClient;

    render(
      <BrowserRouter>
        <AppDataProvider apiClient={apiClient}>
          <TraceProvider>
            <ThreadView />
          </TraceProvider>
        </AppDataProvider>
      </BrowserRouter>,
    );

    expect(screen.getByTestId("queued-controls")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/send a message/i)).toBeInTheDocument();
  });

  it("shows trace indicator for agent event data parts", () => {
    mockMessage = {
      id: "msg-1",
      status: { type: "complete" },
      content: [
        {
          type: "data",
          name: "agent-event",
          data: { agentName: "agent-1", eventType: "start", timestamp: "2026-01-01T00:00:00Z" },
        },
      ],
    };
    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue({
        profiles: [],
        runModes: [],
        defaultRunMode: null,
      }),
      getSettings: vi.fn().mockResolvedValue({
        models: [],
        defaultModel: null,
        toolGroups: [],
        profileDefaults: [],
        inferenceProfiles: [],
        warnings: [],
      }),
      listResources: vi.fn().mockResolvedValue({
        skills: [],
        prompts: [],
        diagnostics: { warnings: [] },
      }),
      getPhoenixConfig: vi.fn().mockResolvedValue({ enabled: false }),
    } as unknown as ApiClient;

    render(
      <BrowserRouter>
        <AppDataProvider apiClient={apiClient}>
          <TraceProvider>
            <ThreadView />
          </TraceProvider>
        </AppDataProvider>
      </BrowserRouter>,
    );

    expect(screen.getByLabelText(/view agent trace/i)).toBeInTheDocument();
  });
});
