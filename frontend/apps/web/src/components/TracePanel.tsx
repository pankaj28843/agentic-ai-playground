import { ArrowRight, Brain, ChevronDown, ChevronRight, Clock, ExternalLink, User, Users, Wrench, X } from "lucide-react";
import type { FC, MouseEvent } from "react";
import { useEffect, useMemo, useRef } from "react";
import hljs from "highlight.js/lib/core";
import json from "highlight.js/lib/languages/json";
import "highlight.js/styles/github-dark.css";

import styles from "./TracePanel.module.css";

// Register JSON language for highlight.js
hljs.registerLanguage("json", json);

export type TraceItem =
  | { type: "thinking"; text: string; timestamp?: string }
  | {
      type: "tool-call";
      toolName: string;
      args: Record<string, unknown>;
      result?: unknown;
      resultFull?: unknown;
      resultTruncated?: boolean;
      status: string;
      isError?: boolean;
      timestamp?: string;
      callingAgent?: string;  // Which agent made this call (in multi-agent modes)
    }
  | {
      type: "agent-event";
      agentName?: string;
      eventType: "start" | "complete" | "handoff";
      fromAgents?: string[];
      toAgents?: string[];
      handoffMessage?: string;  // Reason for handoff
      timestamp?: string;
    };

interface PhoenixLinkProps {
  traceId?: string;
  sessionId?: string;
  // Full URLs from backend (preferred - works across browsers)
  traceUrl?: string;
  sessionUrl?: string;
  // Legacy fields for fallback URL building (deprecated)
  phoenixBaseUrl?: string;
  projectName?: string;
  projectId?: string;
}

interface RuntimeInfo {
  runMode?: string;
  profileName?: string;
  modelId?: string;
  executionMode?: string;
  entrypointReference?: string;
}

interface TracePanelProps {
  items: TraceItem[];
  isOpen: boolean;
  onClose: () => void;
  status?: "running" | "complete";
  startTime?: string; // ISO timestamp of stream start
  phoenix?: PhoenixLinkProps; // Phoenix observability links
  runtime?: RuntimeInfo; // Runtime metadata (mode, profile, model)
  expandedItems: Set<number>;
  onToggleExpanded: (index: number) => void;
  fullOutputItems: Set<number>;
  onToggleFullOutput: (index: number) => void;
}

/**
 * Format elapsed time as T+00:00.000
 */
function formatElapsed(startTime: string | undefined, itemTime: string | undefined): string {
  if (!startTime || !itemTime) return "";
  const start = new Date(startTime).getTime();
  const item = new Date(itemTime).getTime();
  const elapsedMs = item - start;
  if (Number.isNaN(elapsedMs) || elapsedMs < 0) return "";
  const minutes = Math.floor(elapsedMs / 60000);
  const seconds = Math.floor((elapsedMs % 60000) / 1000);
  const ms = elapsedMs % 1000;
  return `T+${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}.${String(ms).padStart(3, "0")}`;
}

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

export const TracePanel: FC<TracePanelProps> = ({
  items,
  isOpen,
  onClose,
  status = "complete",
  startTime,
  phoenix,
  runtime,
  expandedItems,
  onToggleExpanded,
  fullOutputItems,
  onToggleFullOutput,
}) => {
  // Sort items chronologically by timestamp
  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0;
      const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0;
      return timeA - timeB;
    });
  }, [items]);

  // Build Phoenix deep link URLs
  // Prefer full URLs from backend (works across browsers with public URL)
  // Fall back to building locally if legacy fields provided
  const phoenixTraceUrl =
    phoenix?.traceUrl ??
    (phoenix?.phoenixBaseUrl && phoenix?.traceId && phoenix?.projectId
      ? `${phoenix.phoenixBaseUrl}/projects/${phoenix.projectId}/traces/${phoenix.traceId}`
      : null);

  const phoenixSessionUrl =
    phoenix?.sessionUrl ??
    (phoenix?.phoenixBaseUrl && phoenix?.sessionId && phoenix?.projectId
      ? `${phoenix.phoenixBaseUrl}/projects/${phoenix.projectId}/sessions?sessionId=${phoenix.sessionId}`
      : null);

  // When used inside resizable Panel, always render content (Panel handles visibility)
  // When used standalone (mobile), check isOpen
  if (!isOpen) {
    return null;
  }

  const traceStatusClass =
    status === "running" ? styles.traceStatusRunning : styles.traceStatusComplete;

  return (
    <aside className={styles.tracePanel} role="complementary" aria-label="Agent trace">
      <header className={styles.traceHeader}>
        <h2 className={styles.traceTitle}>Agent Trace</h2>
        <span className={cx(styles.traceStatus, traceStatusClass)}>
          {status === "running" ? "Live" : "Complete"}
        </span>
        <button className={styles.traceClose} onClick={onClose} type="button" aria-label="Close trace panel">
          <X aria-hidden="true" />
        </button>
      </header>

        {/* Phoenix observability links */}
        {(phoenixTraceUrl || phoenixSessionUrl) && (
          <div className={styles.tracePhoenixLinks}>
            {phoenixTraceUrl && (
              <a
                href={phoenixTraceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.tracePhoenixLink}
                title={`Phoenix Trace: ${phoenix?.traceId}`}
              >
                <ExternalLink size={14} aria-hidden="true" />
                <span>View in Phoenix</span>
              </a>
            )}
            {phoenixSessionUrl && (
              <a
                href={phoenixSessionUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.tracePhoenixLink}
                title={`Phoenix Session: ${phoenix?.sessionId}`}
              >
                <ExternalLink size={14} aria-hidden="true" />
                <span>Session History</span>
              </a>
            )}
          </div>
        )}

        {/* Runtime metadata (mode, profile, model) */}
        {(runtime?.runMode || runtime?.profileName || runtime?.modelId || runtime?.executionMode || runtime?.entrypointReference) && (
          <div className={styles.traceRuntimeInfo}>
            {runtime.runMode && (
              <span className={styles.traceRuntimeItem} title="Run mode">
                <span className={styles.traceRuntimeLabel}>Mode:</span>
                <span className={styles.traceRuntimeValue}>{runtime.runMode}</span>
              </span>
            )}
            {runtime.executionMode && (
              <span className={styles.traceRuntimeItem} title="Execution mode">
                <span className={styles.traceRuntimeLabel}>Execution:</span>
                <span className={styles.traceRuntimeValue}>{runtime.executionMode}</span>
              </span>
            )}
            {runtime.profileName && (
              <span className={styles.traceRuntimeItem} title="Profile">
                <span className={styles.traceRuntimeLabel}>Profile:</span>
                <span className={styles.traceRuntimeValue}>{runtime.profileName}</span>
              </span>
            )}
            {runtime.entrypointReference && (
              <span className={styles.traceRuntimeItem} title="Entrypoint">
                <span className={styles.traceRuntimeLabel}>Entrypoint:</span>
                <span className={styles.traceRuntimeValue}>{runtime.entrypointReference}</span>
              </span>
            )}
            {runtime.modelId && (
              <span className={styles.traceRuntimeItem} title="Model">
                <span className={styles.traceRuntimeLabel}>Model:</span>
                <span className={styles.traceRuntimeValue}>{runtime.modelId}</span>
              </span>
            )}
          </div>
        )}

        <div className={styles.traceItems}>
          {sortedItems.length === 0 ? (
            <div className={styles.traceEmpty}>No trace data yet</div>
          ) : (
            sortedItems.map((item, index) => (
              <TraceItemView
                key={`${item.type}-${item.timestamp || index}`}
                item={item}
                index={index}
                startTime={startTime}
                expanded={expandedItems.has(index)}
                onToggle={() => onToggleExpanded(index)}
                showFullOutput={fullOutputItems.has(index)}
                onToggleFullOutput={() => onToggleFullOutput(index)}
              />
            ))
          )}
        </div>
      </aside>
  );
};

/**
 * Code block with syntax highlighting
 */
const HighlightedCode: FC<{ code: string; className?: string }> = ({ code, className = "" }) => {
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (codeRef.current) {
      // Try to detect if it's JSON-like for highlighting
      const trimmed = code.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        try {
          // Validate it's JSON before highlighting
          JSON.parse(trimmed);
          hljs.highlightElement(codeRef.current);
        } catch {
          // Not valid JSON, skip highlighting
        }
      }
    }
  }, [code]);

  return (
    <pre className={cx(styles.traceCode, className)}>
      <code ref={codeRef} className="language-json">
        {code}
      </code>
    </pre>
  );
};

const TraceItemView: FC<{
  item: TraceItem;
  index: number;
  startTime?: string;
  expanded: boolean;
  onToggle: () => void;
  showFullOutput: boolean;
  onToggleFullOutput: () => void;
}> = ({ item, startTime, expanded, onToggle, showFullOutput, onToggleFullOutput }) => {
  const elapsed = formatElapsed(startTime, item.timestamp);

  if (item.type === "thinking") {
    return (
      <div className={styles.traceItem}>
        <button
          className={styles.traceItemHeader}
          onClick={onToggle}
          type="button"
          aria-expanded={expanded}
        >
          <span className={cx(styles.traceItemIcon, styles.traceItemIconThinking)}>
            <Brain aria-hidden="true" />
          </span>
          <span className={styles.traceItemLabel}>Thinking</span>
          {elapsed && <span className={styles.traceItemTime}>{elapsed}</span>}
          <span className={styles.traceItemChevron}>
            {expanded ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
          </span>
        </button>
        {expanded && (
          <div className={styles.traceItemContent}>
            <pre className={styles.traceThinkingText}>{item.text}</pre>
          </div>
        )}
      </div>
    );
  }

  if (item.type === "agent-event") {
    // Render agent orchestration events (start, complete, handoff)
    const isHandoff = item.eventType === "handoff";
    const statusText = isHandoff
      ? `${item.fromAgents?.join(", ") || "?"} → ${item.toAgents?.join(", ") || "?"}`
      : item.eventType === "start"
        ? "started"
        : "complete";
    const agentLabel = isHandoff ? "Handoff" : item.agentName || "Agent";
    const hasMessage = isHandoff && item.handoffMessage;
    const agentEventClass =
      item.eventType === "start"
        ? styles.traceAgentEventStart
        : item.eventType === "complete"
          ? styles.traceAgentEventComplete
          : styles.traceAgentEventHandoff;
    const agentIconClass =
      item.eventType === "complete"
        ? styles.traceItemIconAgentComplete
        : item.eventType === "handoff"
          ? styles.traceItemIconAgentHandoff
          : "";
    const agentStatusClass =
      item.eventType === "start"
        ? styles.traceItemStatusStart
        : item.eventType === "complete"
          ? styles.traceItemStatusComplete
          : styles.traceItemStatusHandoff;

    return (
      <div className={cx(styles.traceItem, styles.traceAgentEvent, agentEventClass)}>
        <button
          className={cx(styles.traceItemHeader, styles.traceAgentHeader)}
          onClick={hasMessage ? onToggle : undefined}
          type="button"
          aria-expanded={hasMessage ? expanded : undefined}
          disabled={!hasMessage}
        >
          <span className={cx(styles.traceItemIcon, styles.traceItemIconAgent, agentIconClass)}>
            {isHandoff ? <Users aria-hidden="true" /> : <User aria-hidden="true" />}
          </span>
          <span className={cx(styles.traceItemLabel, styles.traceAgentName)}>{agentLabel}</span>
          {elapsed && <span className={styles.traceItemTime}>{elapsed}</span>}
          <span className={cx(styles.traceItemStatus, agentStatusClass)}>
            {isHandoff && <ArrowRight size={12} aria-hidden="true" className={styles.handoffArrow} />}
            {statusText}
          </span>
          {hasMessage && (
            <span className={styles.traceItemChevron}>
              {expanded ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
            </span>
          )}
        </button>
        {expanded && hasMessage && (
          <div className={styles.traceItemContent}>
            <div className={styles.traceHandoffMessage}>{item.handoffMessage}</div>
          </div>
        )}
      </div>
    );
  }

  // Tool call
  const unwrapMcpContent = (data: unknown): unknown => {
    if (Array.isArray(data) && data.length > 0) {
      // Check if it's MCP format: [{text: "..."}, ...]
      const allText = data.every(
        (item) => typeof item === "object" && item !== null && "text" in item
      );
      if (allText) {
        // Extract text content
        const texts = data.map((item) => {
          const text = (item as { text: string }).text;
          // Try to parse each text as JSON
          try {
            return JSON.parse(text);
          } catch {
            return text;
          }
        });
        return texts.length === 1 ? texts[0] : texts;
      }
    }
    return data;
  };

  const formatResult = (result: unknown): string => {
    if (result === undefined || result === null) return "";
    if (typeof result === "string") {
      // Try to parse as JSON and prettify
      try {
        let parsed = JSON.parse(result);
        // Unwrap MCP content format if present
        parsed = unwrapMcpContent(parsed);
        // Stringify with indentation, then unescape newlines for display
        const formatted = JSON.stringify(parsed, null, 2);
        // Replace escaped newlines in string values with actual newlines
        return formatted.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
      } catch {
        // Not valid JSON - render escaped characters
        return result.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
      }
    }
    // For non-string values, unwrap MCP format and stringify
    const unwrapped = unwrapMcpContent(result);
    const formatted = JSON.stringify(unwrapped, null, 2);
    return formatted.replace(/\\n/g, "\n").replace(/\\t/g, "\t");
  };
  const toolStatusClass =
    item.status === "complete"
      ? styles.traceItemStatusComplete
      : item.status === "error"
        ? styles.traceItemStatusError
        : "";

  const resolvedResult = showFullOutput && item.resultFull !== undefined ? item.resultFull : item.result;
  const argsText = expanded
    ? (typeof item.args === "string" ? item.args : JSON.stringify(item.args ?? {}, null, 2))
    : "";
  const resultText = expanded && resolvedResult !== undefined ? formatResult(resolvedResult) : null;

  return (
    <div className={cx(styles.traceItem, item.isError && styles.traceToolError)}>
      <button
        className={styles.traceItemHeader}
        onClick={onToggle}
        type="button"
        aria-expanded={expanded}
      >
        <span
          className={cx(
            styles.traceItemIcon,
            styles.traceItemIconTool,
            item.isError && styles.traceItemIconError,
          )}
        >
          <Wrench aria-hidden="true" />
        </span>
        <span className={cx(styles.traceItemLabel, styles.traceToolName)}>
          {item.callingAgent && <span className={styles.traceCallingAgent}>[{item.callingAgent}]</span>}
          {item.toolName}
        </span>
        {elapsed && <span className={styles.traceItemTime}>{elapsed}</span>}
        <span className={cx(styles.traceItemStatus, toolStatusClass)}>{item.status}</span>
        <span className={styles.traceItemChevron}>
          {expanded ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
        </span>
      </button>
      {expanded && (
        <div className={styles.traceItemContent}>
          <div className={styles.traceSection}>
            <span className={styles.traceSectionLabel}>Arguments</span>
            <HighlightedCode code={argsText} />
          </div>
          {resultText && (
            <div className={styles.traceSection}>
              <span className={styles.traceSectionLabel}>Result</span>
              {item.resultTruncated && item.resultFull !== undefined && (
                <button
                  type="button"
                  className={styles.traceResultToggle}
                  onClick={onToggleFullOutput}
                >
                  {showFullOutput ? "Show truncated" : "Show full output"}
                </button>
              )}
              <HighlightedCode code={resultText} className={styles.traceResult} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * A compact trace indicator button that shows in the message.
 */
interface TraceIndicatorProps {
  thinkingCount: number;
  toolCallCount: number;
  agentEventCount?: number;
  onClick: () => void;
  isRunning?: boolean;
}

export const TraceIndicator: FC<TraceIndicatorProps> = ({
  thinkingCount,
  toolCallCount,
  agentEventCount = 0,
  onClick,
  isRunning = false,
}) => {
  const total = thinkingCount + toolCallCount + agentEventCount;
  if (total === 0) {
    return null;
  }

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onClick();
  };

  return (
    <button
      className={styles.traceIndicator}
      onClick={handleClick}
      type="button"
      aria-label="View agent trace"
    >
      <Clock className={styles.traceIndicatorIcon} aria-hidden="true" />
      <span className={styles.traceIndicatorText}>
        {isRunning ? "Live trace" : `${total} step${total !== 1 ? "s" : ""}`}
      </span>
      {thinkingCount > 0 && (
        <span className={cx(styles.traceIndicatorBadge, styles.traceIndicatorBadgeThinking)}>
          <Brain aria-hidden="true" />
          {thinkingCount}
        </span>
      )}
      {toolCallCount > 0 && (
        <span className={cx(styles.traceIndicatorBadge, styles.traceIndicatorBadgeTool)}>
          <Wrench aria-hidden="true" />
          {toolCallCount}
        </span>
      )}
      {agentEventCount > 0 && (
        <span className={cx(styles.traceIndicatorBadge, styles.traceIndicatorBadgeAgent)}>
          <Users aria-hidden="true" />
          {agentEventCount}
        </span>
      )}
    </button>
  );
};
