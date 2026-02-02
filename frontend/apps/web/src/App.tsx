import { ApiClient, type PhoenixConfig, type ProfilesResponse } from "@agentic-ai-playground/api-client";
import {
  AssistantRuntimeProvider,
  useThreadRouterSync,
} from "@agentic-ai-playground/assistant-runtime";
import { Bot, Loader2, Menu, Monitor, Moon, Sun, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { ThreadList } from "./components/ThreadList";
import { ThreadNotFound } from "./components/ThreadNotFound";
import { ThreadView } from "./components/ThreadView";
import { TracePanel } from "./components/TracePanel";
import { TraceProvider, useTrace } from "./contexts/TraceContext";
import { useResizableSidebar, useTheme } from "./hooks";
import styles from "./App.module.css";

// Phoenix config context for deep links
interface PhoenixContextValue {
  config: PhoenixConfig | null;
}
const PhoenixContext = createContext<PhoenixContextValue>({ config: null });
export const usePhoenix = () => useContext(PhoenixContext);

const AppContent = ({
  profiles,
  runMode,
  setRunMode,
}: {
  profiles: ProfilesResponse | null;
  runMode: string;
  setRunMode: (mode: string) => void;
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const { conversationId } = useParams<{ conversationId?: string }>();
  const navigate = useNavigate();
  const { theme, cycleTheme } = useTheme();
  const { closeTrace } = useTrace();
  const prevConversationIdRef = useRef(conversationId);

  // Close trace panel when conversation changes (not on initial mount or closeTrace reference changes)
  useEffect(() => {
    if (prevConversationIdRef.current !== conversationId) {
      closeTrace();
      prevConversationIdRef.current = conversationId;
    }
  }, [conversationId, closeTrace]);

  const ThemeIcon = theme === "system" ? Monitor : theme === "dark" ? Moon : Sun;

  const onThreadChange = useCallback(
    (threadId: string | null) => {
      if (threadId) {
        navigate(`/c/${threadId}`, { replace: true });
      } else {
        // Only navigate to /new if not already there
        // Read pathname directly to get current value
        if (window.location.pathname !== "/new") {
          navigate("/new", { replace: true });
        }
      }
    },
    [navigate],
  );

  const { isLoadingThread, threadNotFound } = useThreadRouterSync(conversationId, onThreadChange);

  const handleGoHome = useCallback(() => {
    // Only navigate if not already on /new
    if (window.location.pathname !== "/new") {
      navigate("/new", { replace: true });
    }
  }, [navigate]);

  const handleLogoClick = useCallback(() => {
    // Navigate to /new (which is home)
    if (window.location.pathname !== "/new") {
      navigate("/new");
    }
  }, [navigate]);

  // Show loading state when loading a thread from URL
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

  const { trace } = useTrace();
  const isTraceOpen = trace.isOpen;

  // Custom resizable sidebar hook - stores pixel widths in localStorage
  const {
    sidebarWidth,
    traceWidth,
    sidebarResizeHandleProps,
    traceResizeHandleProps,
    isResizing,
  } = useResizableSidebar();

  // Sidebar content component for reuse
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
      </div>

      <div className={styles.sidebarControls}>
        <label className={styles.controlRow}>
          <span>Mode</span>
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
          onClick={() => setMenuOpen((open) => !open)}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
        >
          {menuOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
        <span className={styles.mobileTitle}>Playground</span>
      </header>
      <button
        className={styles.mobileOverlay}
        type="button"
        onClick={() => setMenuOpen(false)}
        aria-label="Close navigation"
      />

      {/* Mobile sidebar */}
      <aside className={`${styles.appSidebar} ${styles.mobileOnly}`}>
        {sidebarContent}
      </aside>

      {/* Desktop layout with resizable panels */}
      <div className={styles.desktopLayout}>
        {/* Left sidebar */}
        <aside
          className={`${styles.appSidebar} ${styles.desktopOnly}`}
          style={{ width: sidebarWidth, flexShrink: 0 }}
        >
          {sidebarContent}
        </aside>

        {/* Sidebar resize handle */}
        <div
          className={styles.resizeHandle}
          role="separator"
          aria-orientation="vertical"
          tabIndex={0}
          {...sidebarResizeHandleProps}
        />

        {/* Main content */}
        <main className={styles.appMain}>
          {renderMainContent()}
        </main>

        {/* Trace panel (conditional) */}
        {isTraceOpen && (
          <>
            {/* Trace resize handle */}
            <div
              className={styles.resizeHandle}
              role="separator"
              aria-orientation="vertical"
              tabIndex={0}
              {...traceResizeHandleProps}
            />

            {/* Trace panel */}
            <div className={styles.tracePanelContainer} style={{ width: traceWidth, flexShrink: 0 }}>
              <TracePanelOutlet />
            </div>
          </>
        )}
      </div>

      {/* Mobile trace backdrop */}
      {isTraceOpen && (
        <button className={styles.traceBackdrop} onClick={closeTrace} type="button" aria-label="Close trace" />
      )}
    </div>
  );
};

/** Renders the trace panel using context state */
const TracePanelOutlet: React.FC = () => {
  const { trace, expandedItems, closeTrace, toggleItemExpanded } = useTrace();
  const { config: phoenixConfig } = usePhoenix();
  return (
    <TracePanel
      items={trace.items}
      isOpen={trace.isOpen}
      onClose={closeTrace}
      status={trace.status}
      startTime={trace.startTime}
      expandedItems={expandedItems}
      onToggleExpanded={toggleItemExpanded}
      phoenix={
        phoenixConfig?.enabled || trace.phoenix?.traceUrl || trace.phoenix?.sessionUrl
          ? {
              traceId: trace.phoenix?.traceId,
              sessionId: trace.phoenix?.sessionId,
              // Prefer URLs from message metadata (set via openTrace)
              traceUrl: trace.phoenix?.traceUrl,
              sessionUrl: trace.phoenix?.sessionUrl,
              // Legacy fallback fields
              phoenixBaseUrl: phoenixConfig?.baseUrl,
              projectName: phoenixConfig?.projectName,
              projectId: phoenixConfig?.projectId,
            }
          : undefined
      }
      runtime={trace.runtime}
    />
  );
};

export const App = () => {
  const [profiles, setProfiles] = useState<ProfilesResponse | null>(null);
  const [runMode, setRunMode] = useState<string>("");
  const [phoenixConfig, setPhoenixConfig] = useState<PhoenixConfig | null>(null);

  const apiClient = useMemo(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    return new ApiClient(baseUrl);
  }, []);

  // Fetch profiles and Phoenix config on mount
  useEffect(() => {
    let cancelled = false;
    apiClient
      .listProfiles()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setProfiles(response);
        const defaultRunMode =
          response.defaultRunMode ??
          response.runModes[0] ??
          response.profiles[0]?.id ??
          "";
        setRunMode(defaultRunMode);
      })
      .catch(() => {
        if (!cancelled) {
          setProfiles({ profiles: [], runModes: [], defaultRunMode: null });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [apiClient]);

  // Fetch Phoenix config separately
  useEffect(() => {
    let cancelled = false;
    apiClient
      .getPhoenixConfig()
      .then((config) => {
        if (!cancelled) {
          setPhoenixConfig(config);
        }
      })
      .catch(() => {
        // Phoenix may not be enabled - that's fine
      });
    return () => {
      cancelled = true;
    };
  }, [apiClient]);

  return (
    <PhoenixContext.Provider value={{ config: phoenixConfig }}>
      <TraceProvider>
        <AssistantRuntimeProvider runMode={runMode}>
          <AppContent
            profiles={profiles}
            runMode={runMode}
            setRunMode={setRunMode}
          />
        </AssistantRuntimeProvider>
      </TraceProvider>
    </PhoenixContext.Provider>
  );
};
