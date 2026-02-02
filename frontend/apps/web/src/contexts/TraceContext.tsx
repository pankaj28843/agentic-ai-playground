import { phoenixMetadataEvents, runtimeMetadataEvents, type PhoenixTraceMetadata, type RuntimeMetadata } from "@agentic-ai-playground/api-client";
import { createContext, useCallback, useContext, useEffect, useState, type FC, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import type { TraceItem } from "../components/TracePanel";

const TRACE_EXPANDED_STORAGE_KEY = "playground-trace-expanded";

interface PhoenixMetadata {
  traceId?: string;
  sessionId?: string;
  // Full URLs from backend (preferred) or built locally as fallback
  traceUrl?: string;
  sessionUrl?: string;
}

interface TraceState {
  items: TraceItem[];
  isOpen: boolean;
  status: "running" | "complete";
  startTime?: string;
  messageId?: string; // Track which message's trace is being shown
  phoenix?: PhoenixMetadata; // Phoenix observability metadata
  runtime?: RuntimeMetadata; // Runtime metadata (mode, profile, model)
}

/** Get expanded item indices from localStorage */
function loadExpandedItems(messageId: string): Set<number> {
  if (typeof window === "undefined") return new Set();
  try {
    const stored = localStorage.getItem(`${TRACE_EXPANDED_STORAGE_KEY}:${messageId}`);
    if (stored) {
      const parsed = JSON.parse(stored);
      if (Array.isArray(parsed)) {
        return new Set(parsed);
      }
    }
  } catch {
    // Ignore storage errors
  }
  return new Set();
}

/** Save expanded item indices to localStorage */
function saveExpandedItems(messageId: string, indices: Set<number>): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(`${TRACE_EXPANDED_STORAGE_KEY}:${messageId}`, JSON.stringify([...indices]));
  } catch {
    // Ignore storage errors
  }
}

/** Clear expanded items from localStorage */
function clearExpandedItems(messageId: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(`${TRACE_EXPANDED_STORAGE_KEY}:${messageId}`);
  } catch {
    // Ignore storage errors
  }
}

interface TraceContextValue {
  trace: TraceState;
  expandedItems: Set<number>;
  openTrace: (params: {
    items: TraceItem[];
    status: "running" | "complete";
    startTime?: string;
    messageId: string;
    phoenix?: PhoenixMetadata;
    runtime?: RuntimeMetadata;
  }) => void;
  closeTrace: () => void;
  updateTrace: (params: {
    items?: TraceItem[];
    status?: "running" | "complete";
    startTime?: string;
    phoenix?: PhoenixMetadata;
    runtime?: RuntimeMetadata;
  }) => void;
  toggleItemExpanded: (index: number) => void;
}

const TraceContext = createContext<TraceContextValue | null>(null);

export const TraceProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [trace, setTrace] = useState<TraceState>({
    items: [],
    isOpen: false,
    status: "complete",
  });
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  // Initialize from URL on mount - restore trace state
  useEffect(() => {
    const traceId = searchParams.get("trace_id");
    if (traceId && !trace.isOpen) {
      setTrace((prev) => ({
        ...prev,
        isOpen: true,
        messageId: traceId,
      }));
      setExpandedItems(loadExpandedItems(traceId));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only run on mount to restore state from URL
  }, []);

  // Subscribe to Phoenix metadata events from streaming (for live updates)
  useEffect(() => {
    const unsubscribe = phoenixMetadataEvents.subscribe((metadata: PhoenixTraceMetadata) => {
      setTrace((prev) => ({
        ...prev,
        phoenix: {
          ...prev.phoenix,
          traceId: metadata.traceId ?? prev.phoenix?.traceId,
          sessionId: metadata.sessionId ?? prev.phoenix?.sessionId,
          // Note: URLs come from backend via openTrace with stored message data
        },
      }));
    });
    return unsubscribe;
  }, []);

  // Subscribe to runtime metadata events from streaming
  useEffect(() => {
    const unsubscribe = runtimeMetadataEvents.subscribe((metadata: RuntimeMetadata) => {
      setTrace((prev) => ({
        ...prev,
        runtime: {
          runMode: metadata.runMode ?? prev.runtime?.runMode,
          profileName: metadata.profileName ?? prev.runtime?.profileName,
          modelId: metadata.modelId ?? prev.runtime?.modelId,
          executionMode: metadata.executionMode ?? prev.runtime?.executionMode,
          entrypointReference: metadata.entrypointReference ?? prev.runtime?.entrypointReference,
        },
      }));
    });
    return unsubscribe;
  }, []);

  const openTrace = useCallback(
    (params: {
      items: TraceItem[];
      status: "running" | "complete";
      startTime?: string;
      messageId: string;
      phoenix?: PhoenixMetadata;
      runtime?: RuntimeMetadata;
    }) => {
      setTrace((prev) => ({
        items: params.items,
        isOpen: true,
        status: params.status,
        startTime: params.startTime,
        messageId: params.messageId,
        phoenix: params.phoenix ?? prev.phoenix,
        runtime: params.runtime ?? prev.runtime,
      }));

      // Only update URL with trace_id if we're on a conversation page (not /new)
      // Check if current path starts with /c/
      const currentPath = window.location.pathname;
      if (currentPath.startsWith("/c/")) {
        setSearchParams((prev) => {
          const newParams = new URLSearchParams(prev);
          newParams.set("trace_id", params.messageId);
          return newParams;
        }, { replace: true });
      }

      // Load expanded items for this message
      setExpandedItems(loadExpandedItems(params.messageId));
    },
    [setSearchParams],
  );

  const closeTrace = useCallback(() => {
    const messageId = trace.messageId;

    setTrace((prev) => ({
      ...prev,
      isOpen: false,
      items: [],
      messageId: undefined,
      // Keep phoenix metadata so Session History link persists
    }));

    // Only clear URL param if we're on a conversation page
    const currentPath = window.location.pathname;
    if (currentPath.startsWith("/c/")) {
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev);
        newParams.delete("trace_id");
        return newParams;
      }, { replace: true });
    }

    // Clear expanded items from storage
    if (messageId) {
      clearExpandedItems(messageId);
    }
    setExpandedItems(new Set());
  }, [trace.messageId, setSearchParams]);

  const updateTrace = useCallback(
    (params: {
      items?: TraceItem[];
      status?: "running" | "complete";
      startTime?: string;
      phoenix?: PhoenixMetadata;
      runtime?: RuntimeMetadata;
    }) => {
      setTrace((prev) => ({
        ...prev,
        ...(params.items !== undefined && { items: params.items }),
        ...(params.status !== undefined && { status: params.status }),
        ...(params.startTime !== undefined && { startTime: params.startTime }),
        ...(params.phoenix !== undefined && { phoenix: params.phoenix }),
        ...(params.runtime !== undefined && { runtime: params.runtime }),
      }));
    },
    [],
  );

  const toggleItemExpanded = useCallback((index: number) => {
    setExpandedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      // Save to localStorage
      if (trace.messageId) {
        saveExpandedItems(trace.messageId, newSet);
      }
      return newSet;
    });
  }, [trace.messageId]);

  return (
    <TraceContext.Provider value={{ trace, expandedItems, openTrace, closeTrace, updateTrace, toggleItemExpanded }}>
      {children}
    </TraceContext.Provider>
  );
};

export const useTrace = (): TraceContextValue => {
  const context = useContext(TraceContext);
  if (!context) {
    throw new Error("useTrace must be used within a TraceProvider");
  }
  return context;
};
