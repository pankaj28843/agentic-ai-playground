import type { ReactNode } from "react";

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProfilesResponse } from "@agentic-ai-playground/api-client";
import { App, AppContent, AppShell } from "../App";
import { AppShellProvider } from "../state/appShellContext";

let mockConversationId: string | undefined = "thread-1";
const navigateMock = vi.fn();
const closeTraceMock = vi.fn();
const cycleThemeMock = vi.fn();

let traceOpen = false;
let loadingThread = false;
let threadNotFound = false;
let mockTheme: "system" | "dark" | "light" = "system";

vi.mock("react-router-dom", () => ({
  useParams: () => ({ conversationId: mockConversationId }),
  useNavigate: () => navigateMock,
}));

vi.mock("@agentic-ai-playground/assistant-runtime", () => ({
  useThreadRouterSync: () => ({ isLoadingThread: loadingThread, threadNotFound }),
  AssistantRuntimeProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="runtime">{children}</div>
  ),
}));

vi.mock("../hooks", () => ({
  useTheme: () => ({ theme: mockTheme, cycleTheme: cycleThemeMock }),
  useResizableSidebar: () => ({
    sidebarWidth: 240,
    traceWidth: 320,
    sidebarResizeHandleProps: {},
    traceResizeHandleProps: {},
    isResizing: false,
  }),
}));

vi.mock("../contexts/TraceContext", () => ({
  TraceProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="trace-provider">{children}</div>
  ),
  useTrace: () => ({
    trace: { isOpen: traceOpen, items: [], status: "complete" },
    expandedItems: new Set(),
    fullOutputItems: new Set(),
    closeTrace: closeTraceMock,
    toggleItemExpanded: vi.fn(),
    toggleItemOutput: vi.fn(),
  }),
}));

const appDataSendMock = vi.fn();

vi.mock("../state/appDataContext", () => ({
  AppDataProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="app-data">{children}</div>
  ),
  useAppDataActor: () => ({ send: appDataSendMock }),
  useAppDataSelector: (
    selector: (snapshot: { context: { profiles: ProfilesResponse; runMode: string; phoenixConfig: null } }) => unknown,
  ) =>
    selector({
      context: {
        profiles: {
          profiles: [
            {
              id: "quick",
              name: "Quick",
              description: "",
              entrypointType: "single",
              entrypointReference: "general",
              default: true,
              metadata: {},
            },
          ],
          runModes: ["quick"],
          defaultRunMode: "quick",
        },
        runMode: "quick",
        phoenixConfig: null,
      },
    }),
}));

vi.mock("../state/useOverrides", () => ({}));

vi.mock("../state/overridesContext", () => ({}));

vi.mock("../state/themeContext", () => ({
  ThemeProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="theme">{children}</div>
  ),
}));

vi.mock("../state/layoutContext", () => ({
  LayoutProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="layout">{children}</div>
  ),
}));

vi.mock("../contexts/SessionTreeContext", () => ({
  SessionTreeProvider: ({ children }: { children: ReactNode }) => (
    <div data-testid="session-tree">{children}</div>
  ),
}));

vi.mock("../components/ThreadList", () => ({ ThreadList: () => <div>ThreadList</div> }));
vi.mock("../components/SessionTreePanel", () => ({ SessionTreePanel: () => <div>SessionTree</div> }));
vi.mock("../components/ThreadView", () => ({ ThreadView: () => <div>ThreadView</div> }));
vi.mock("../components/ThreadNotFound", () => ({
  ThreadNotFound: ({ onGoHome }: { onGoHome: () => void }) => (
    <button type="button" onClick={onGoHome}>
      NotFound
    </button>
  ),
}));
vi.mock("../components/TracePanel", () => ({ TracePanel: () => <div>TracePanel</div> }));

const profiles: ProfilesResponse = {
  profiles: [
    {
      id: "quick",
      name: "Quick",
      description: "",
      entrypointType: "single",
      entrypointReference: "general",
      default: true,
      metadata: {},
    },
  ],
  runModes: ["quick"],
  defaultRunMode: "quick",
};

describe("AppContent", () => {
  beforeEach(() => {
    navigateMock.mockClear();
    closeTraceMock.mockClear();
    cycleThemeMock.mockClear();
    appDataSendMock.mockClear();
    mockTheme = "system";
    mockConversationId = "thread-1";
    window.history.pushState({}, "", "/");
    loadingThread = false;
    threadNotFound = false;
    traceOpen = false;
  });
  afterEach(() => {
    cleanup();
  });
  it("renders loading state", () => {
    loadingThread = true;
    threadNotFound = false;

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    expect(screen.getByText("Loading conversation...")).toBeInTheDocument();
  });

  it("renders not found view and navigates home", () => {
    loadingThread = false;
    threadNotFound = true;

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    fireEvent.click(screen.getByText("NotFound"));
    expect(navigateMock).toHaveBeenCalledWith("/new", { replace: true });
  });

  it("renders thread view and trace panel", () => {
    loadingThread = false;
    threadNotFound = false;
    traceOpen = true;

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    expect(screen.getByText("ThreadView")).toBeInTheDocument();
    expect(screen.getByText("TracePanel")).toBeInTheDocument();
  });

  it("renders with dark theme icon branch", () => {
    loadingThread = false;
    threadNotFound = false;
    traceOpen = false;
    mockTheme = "dark";

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    expect(screen.getAllByLabelText("Theme: dark. Click to change.").length).toBeGreaterThan(0);
  });

  it("renders with light theme icon branch", () => {
    loadingThread = false;
    threadNotFound = false;
    traceOpen = false;
    mockTheme = "light";

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    expect(screen.getAllByLabelText("Theme: light. Click to change.").length).toBeGreaterThan(0);
  });

  it("toggles menu and updates theme", () => {
    loadingThread = false;
    threadNotFound = false;
    traceOpen = false;

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    const menuToggle = screen.getAllByLabelText("Open navigation")[0];
    fireEvent.click(menuToggle);
    expect(screen.getAllByLabelText("Close navigation").length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByLabelText("Close navigation")[0]);

    const themeButton = screen.getAllByLabelText("Theme: system. Click to change.")[0];
    fireEvent.click(themeButton);
    expect(cycleThemeMock).toHaveBeenCalled();
  });

  it("closes trace on conversation change", () => {
    loadingThread = false;
    threadNotFound = false;
    traceOpen = false;

    mockConversationId = "thread-1";
    const { rerender } = render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    mockConversationId = "thread-2";
    rerender(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    expect(closeTraceMock).toHaveBeenCalled();
  });

  it("skips loading state when no conversation id", () => {
    loadingThread = true;
    threadNotFound = false;
    mockConversationId = undefined;

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    expect(screen.queryByText("Loading conversation...")).not.toBeInTheDocument();
    expect(screen.getByText("ThreadView")).toBeInTheDocument();
  });

  it("avoids navigation when already on /new", () => {
    loadingThread = false;
    threadNotFound = true;
    window.history.pushState({}, "", "/new");

    render(
      <AppShellProvider>
        <AppContent profiles={profiles} runMode="quick" setRunMode={vi.fn()} />
      </AppShellProvider>,
    );

    fireEvent.click(screen.getByText("NotFound"));
    expect(navigateMock).not.toHaveBeenCalledWith("/new", { replace: true });
  });
});

describe("AppShell", () => {
  it("renders runtime and forwards run mode updates", () => {
    loadingThread = false;
    threadNotFound = false;
    traceOpen = false;

    render(
      <AppShellProvider>
        <AppShell />
      </AppShellProvider>,
    );

    fireEvent.change(screen.getAllByDisplayValue("Quick")[0], { target: { value: "quick" } });
    expect(appDataSendMock).toHaveBeenCalledWith({ type: "RUNMODE.SET", value: "quick" });
    expect(screen.getByTestId("runtime")).toBeInTheDocument();
  });
});

describe("App", () => {
  it("wraps providers", () => {
    render(<App />);
    expect(screen.getByTestId("app-data")).toBeInTheDocument();
    expect(screen.getByTestId("theme")).toBeInTheDocument();
    expect(screen.getByTestId("layout")).toBeInTheDocument();
  });
});
