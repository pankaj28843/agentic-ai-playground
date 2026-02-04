import {
  ApiClient,
  type ProfilesResponse,
} from "@agentic-ai-playground/api-client";
import {
  AssistantRuntimeProvider,
  type RunOverrides,
  useThreadRouterSync,
} from "@agentic-ai-playground/assistant-runtime";
import { Bot, Loader2, Menu, Monitor, Moon, Sun, X } from "lucide-react";
import { useCallback, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { SettingsPanel } from "./components/SettingsPanel";
import { SessionTreePanel } from "./components/SessionTreePanel";
import { ThreadList } from "./components/ThreadList";
import { ThreadNotFound } from "./components/ThreadNotFound";
import { ThreadView } from "./components/ThreadView";
import { TracePanel } from "./components/TracePanel";
import { SessionTreeProvider } from "./contexts/SessionTreeContext";
import { TraceProvider, useTrace } from "./contexts/TraceContext";
import { useResizableSidebar, useTheme } from "./hooks";
import { AppDataProvider, useAppDataActor, useAppDataSelector } from "./state/appDataContext";
import { AppShellProvider, useAppShell } from "./state/appShellContext";
import { LayoutProvider } from "./state/layoutContext";
import { OverridesProvider } from "./state/overridesContext";
import { useOverrides } from "./state/useOverrides";
import { ThemeProvider } from "./state/themeContext";
import styles from "./App.module.css";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const apiClient = new ApiClient(baseUrl);

export const AppContent = ({
  profiles,
  runMode,
  setRunMode,
}: {
  profiles: ProfilesResponse | null;
  runMode: string;
  setRunMode: (mode: string) => void;
}) => {
  const { conversationId } = useParams<{ conversationId?: string }>();
  const navigate = useNavigate();
  const { theme, cycleTheme } = useTheme();
  const { trace, closeTrace } = useTrace();
  const {
    menuOpen,
    toggleMenu,
    closeMenu,
    shouldCloseTrace,
    setConversationId,
    acknowledgeTraceClosed,
  } = useAppShell();

  useEffect(() => {
    setConversationId(conversationId ?? null);
  }, [conversationId, setConversationId]);

  useEffect(() => {
    if (!shouldCloseTrace) {
      return;
    }
    closeTrace();
    acknowledgeTraceClosed();
  }, [acknowledgeTraceClosed, closeTrace, shouldCloseTrace]);

  const ThemeIcon = theme === "system" ? Monitor : theme === "dark" ? Moon : Sun;

  const onThreadChange = useCallback(
    (threadId: string | null) => {
      if (threadId) {
        navigate(`/c/${threadId}`, { replace: true });
      } else {
        if (window.location.pathname !== "/new") {
          navigate("/new", { replace: true });
        }
      }
    },
    [navigate],
  );

  const { isLoadingThread, threadNotFound } = useThreadRouterSync(
    conversationId,
    onThreadChange,
  );


  const handleGoHome = () => {
    if (window.location.pathname !== "/new") {
      navigate("/new", { replace: true });
    }
  };

  const handleLogoClick = () => {
    if (window.location.pathname !== "/new") {
      navigate("/new");
    }
  };

  const renderMainContent = () => {
    if (isLoadingThread && conversationId) {
      return (
        <div className={styles.threadLoading}>
          <Loader2 className={styles.threadLoadingSpinner} aria-hidden="true" />
          <span>Loading conversation...</span>
        </div>
      );
    }

    if (threadNotFound) {
      return <ThreadNotFound onGoHome={handleGoHome} />;
    }

    return <ThreadView />;
  };

  const isTraceOpen = trace.isOpen;

  const {
    sidebarWidth,
    traceWidth,
    sidebarResizeHandleProps,
    traceResizeHandleProps,
    isResizing,
  } = useResizableSidebar();

  const sidebarContent = (
    <>
      <div className={styles.brand}>
        <button
          className={styles.brandLink}
          onClick={handleLogoClick}
          type="button"
          aria-label="Go to home"
        >
          <div className={styles.brandIcon}>
            <Bot aria-hidden="true" />
          </div>
          <span className={styles.brandTitle}>Playground</span>
        </button>
        <button
          className={styles.themeToggle}
          type="button"
          onClick={cycleTheme}
          aria-label={`Theme: ${theme}. Click to change.`}
          title={`Theme: ${theme}`}
        >
          <ThemeIcon aria-hidden="true" />
        </button>
      </div>

      <div className={styles.sidebarThreads}>
        <ThreadList />
        <SessionTreePanel />
      </div>

      <div className={styles.sidebarControls}>
        <label className={styles.controlRow}>
          <span>Run mode</span>
          <select
            value={runMode}
            onChange={(event) => setRunMode(event.target.value)}
            disabled={!profiles?.profiles?.length}
          >
            {(profiles?.profiles ?? []).map((profile) => {
              const label = profile.description
                ? `${profile.name} - ${profile.description}`
                : profile.name;
              return (
                <option key={profile.id} value={profile.id}>
                  {label}
                </option>
              );
            })}
          </select>
        </label>
        <SettingsPanel profiles={profiles} runMode={runMode} />
      </div>
    </>
  );

  return (
    <div
      className={`${styles.appShell} ${menuOpen ? styles.menuOpen : ""} ${isResizing ? styles.isResizing : ""}`}
    >
      <header className={styles.mobileHeader}>
        <button
          className={styles.mobileNavToggle}
          type="button"
          onClick={toggleMenu}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
        >
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
        <span className={styles.mobileTitle}>Playground</span>
      </header>
      <button
        className={styles.mobileOverlay}
        type="button"
        onClick={closeMenu}
        aria-label="Close navigation"
      />

      <aside className={`${styles.appSidebar} ${styles.mobileOnly}`}>{sidebarContent}</aside>

      <div className={styles.desktopLayout}>
        <aside
          className={`${styles.appSidebar} ${styles.desktopOnly}`}
          style={{ width: sidebarWidth, flexShrink: 0 }}
        >
          {sidebarContent}
        </aside>

        <div
          className={styles.resizeHandle}
          role="separator"
          aria-orientation="vertical"
          tabIndex={0}
          {...sidebarResizeHandleProps}
        />

        <main className={styles.appMain}>{renderMainContent()}</main>

        {isTraceOpen && (
          <>
            <div
              className={styles.resizeHandle}
              role="separator"
              aria-orientation="vertical"
              tabIndex={0}
              {...traceResizeHandleProps}
            />

            <div className={styles.tracePanelContainer} style={{ width: traceWidth, flexShrink: 0 }}>
              <TracePanelOutlet />
            </div>
          </>
        )}
      </div>

      {isTraceOpen && (
        <button
          className={styles.traceBackdrop}
          onClick={closeTrace}
          type="button"
          aria-label="Close trace"
        />
      )}
    </div>
  );
};

export const TracePanelOutlet: React.FC = () => {
  const { trace, expandedItems, fullOutputItems, closeTrace, toggleItemExpanded, toggleItemOutput } =
    useTrace();
  const phoenixConfig = useAppDataSelector((state) => state.context.phoenixConfig);
  const phoenixLinks =
    !phoenixConfig?.enabled && !trace.phoenix?.traceUrl && !trace.phoenix?.sessionUrl
      ? undefined
      : {
          traceId: trace.phoenix?.traceId,
          sessionId: trace.phoenix?.sessionId,
          traceUrl: trace.phoenix?.traceUrl,
          sessionUrl: trace.phoenix?.sessionUrl,
          phoenixBaseUrl: phoenixConfig?.baseUrl,
          projectName: phoenixConfig?.projectName,
          projectId: phoenixConfig?.projectId,
        };

  return (
    <TracePanel
      items={trace.items}
      isOpen={trace.isOpen}
      onClose={closeTrace}
      status={trace.status}
      startTime={trace.startTime}
      expandedItems={expandedItems}
      onToggleExpanded={toggleItemExpanded}
      fullOutputItems={fullOutputItems}
      onToggleFullOutput={toggleItemOutput}
      phoenix={phoenixLinks}
      runtime={trace.runtime}
    />
  );
};

export const AppShell = () => {
  const profiles = useAppDataSelector((state) => state.context.profiles);
  const runMode = useAppDataSelector((state) => state.context.runMode);
  const actorRef = useAppDataActor();
  const { modelOverride, toolGroupsOverride } = useOverrides();

  const setRunMode = (mode: string) => {
    actorRef.send({ type: "RUNMODE.SET", value: mode });
  };

  const runOverrides: RunOverrides = {
    modelOverride,
    toolGroupsOverride,
  };

  return (
    <TraceProvider>
      <AssistantRuntimeProvider runMode={runMode} runOverrides={runOverrides}>
        <SessionTreeProvider>
          <AppContent profiles={profiles} runMode={runMode} setRunMode={setRunMode} />
        </SessionTreeProvider>
      </AssistantRuntimeProvider>
    </TraceProvider>
  );
};

export const App = () => {
  const { conversationId } = useParams<{ conversationId?: string }>();

  return (
    <AppDataProvider apiClient={apiClient}>
      <OverridesProvider apiClient={apiClient} threadId={conversationId ?? null}>
        <ThemeProvider>
          <LayoutProvider>
            <AppShellProvider>
              <AppShell />
            </AppShellProvider>
          </LayoutProvider>
        </ThemeProvider>
      </OverridesProvider>
    </AppDataProvider>
  );
};
