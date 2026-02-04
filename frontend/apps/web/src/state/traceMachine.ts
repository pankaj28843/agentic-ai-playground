import { assign, setup } from "xstate";

import type {
  PhoenixTraceMetadata,
  RuntimeMetadata,
} from "@agentic-ai-playground/api-client";
import type { TraceItem } from "../components/TracePanel";

type PhoenixMetadata = {
  traceId?: string;
  sessionId?: string;
  traceUrl?: string;
  sessionUrl?: string;
};

type TraceState = {
  items: TraceItem[];
  isOpen: boolean;
  status: "running" | "complete";
  startTime?: string;
  messageId?: string;
  phoenix?: PhoenixMetadata;
  runtime?: RuntimeMetadata;
};

type TraceContext = {
  trace: TraceState;
  expandedItems: Set<number>;
  fullOutputItems: Set<number>;
};

type TraceInput = {
  initialTraceId: string | null;
};

type TraceEvent =
  | {
      type: "TRACE.OPEN";
      items: TraceItem[];
      status: "running" | "complete";
      startTime?: string;
      messageId: string;
      phoenix?: PhoenixMetadata;
      runtime?: RuntimeMetadata;
    }
  | { type: "TRACE.CLOSE" }
  | {
      type: "TRACE.UPDATE";
      items?: TraceItem[];
      status?: "running" | "complete";
      startTime?: string;
      phoenix?: PhoenixMetadata;
      runtime?: RuntimeMetadata;
    }
  | { type: "TRACE.TOGGLE_EXPANDED"; index: number }
  | { type: "TRACE.TOGGLE_FULL_OUTPUT"; index: number }
  | { type: "TRACE.RESTORE"; messageId: string }
  | { type: "PHOENIX.METADATA"; metadata: PhoenixTraceMetadata }
  | { type: "RUNTIME.METADATA"; metadata: RuntimeMetadata };

const TRACE_EXPANDED_STORAGE_KEY = "playground-trace-expanded";

const loadExpandedItems = (messageId: string): Set<number> => {
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
};

const saveExpandedItems = (messageId: string, indices: Set<number>): void => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(`${TRACE_EXPANDED_STORAGE_KEY}:${messageId}`, JSON.stringify([...indices]));
  } catch {
    // Ignore storage errors
  }
};

const clearExpandedItems = (messageId: string): void => {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(`${TRACE_EXPANDED_STORAGE_KEY}:${messageId}`);
  } catch {
    // Ignore storage errors
  }
};

export const traceMachine = setup({
  types: {
    context: {} as TraceContext,
    input: {} as TraceInput,
    events: {} as TraceEvent,
  },
  actions: {
    openTrace: assign(({ context, event }) => {
      const params = event as Extract<TraceEvent, { type: "TRACE.OPEN" }>;
      const expandedItems = loadExpandedItems(params.messageId);
      return {
        trace: {
          items: params.items,
          isOpen: true,
          status: params.status,
          startTime: params.startTime,
          messageId: params.messageId,
          phoenix: params.phoenix ?? context.trace.phoenix,
          runtime: params.runtime ?? context.trace.runtime,
        },
        expandedItems,
        fullOutputItems: new Set<number>(),
      };
    }),
    restoreTrace: assign(({ event, context }) => {
      const messageId = (event as { messageId: string }).messageId;
      return {
        trace: {
          ...context.trace,
          isOpen: true,
          messageId,
        },
        expandedItems: loadExpandedItems(messageId),
      };
    }),
    closeTrace: assign(({ context }) => {
      if (context.trace.messageId) {
        clearExpandedItems(context.trace.messageId);
      }
      return {
        trace: {
          ...context.trace,
          items: [],
          isOpen: false,
          messageId: undefined,
        },
        expandedItems: new Set<number>(),
        fullOutputItems: new Set<number>(),
      };
    }),
    updateTrace: assign(({ context, event }) => {
      const params = event as Extract<TraceEvent, { type: "TRACE.UPDATE" }>;
      return {
        trace: {
          ...context.trace,
          ...(params.items !== undefined && { items: params.items }),
          ...(params.status !== undefined && { status: params.status }),
          ...(params.startTime !== undefined && { startTime: params.startTime }),
          ...(params.phoenix !== undefined && { phoenix: params.phoenix }),
          ...(params.runtime !== undefined && { runtime: params.runtime }),
        },
      };
    }),
    updatePhoenix: assign(({ context, event }) => {
      const metadata = (event as Extract<TraceEvent, { type: "PHOENIX.METADATA" }>).metadata;
      return {
        trace: {
          ...context.trace,
          phoenix: {
            ...context.trace.phoenix,
            traceId: metadata.traceId ?? context.trace.phoenix?.traceId,
            sessionId: metadata.sessionId ?? context.trace.phoenix?.sessionId,
          },
        },
      };
    }),
    updateRuntime: assign(({ context, event }) => {
      const metadata = (event as Extract<TraceEvent, { type: "RUNTIME.METADATA" }>).metadata;
      return {
        trace: {
          ...context.trace,
          runtime: {
            runMode: metadata.runMode ?? context.trace.runtime?.runMode,
            profileName: metadata.profileName ?? context.trace.runtime?.profileName,
            modelId: metadata.modelId ?? context.trace.runtime?.modelId,
            executionMode: metadata.executionMode ?? context.trace.runtime?.executionMode,
            entrypointReference:
              metadata.entrypointReference ?? context.trace.runtime?.entrypointReference,
          },
        },
      };
    }),
    toggleExpanded: assign(({ context, event }) => {
      const index = (event as Extract<TraceEvent, { type: "TRACE.TOGGLE_EXPANDED" }>).index;
      const next = new Set(context.expandedItems);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      if (context.trace.messageId) {
        saveExpandedItems(context.trace.messageId, next);
      }
      return { expandedItems: next };
    }),
    toggleFullOutput: assign(({ context, event }) => {
      const index = (event as Extract<TraceEvent, { type: "TRACE.TOGGLE_FULL_OUTPUT" }>).index;
      const next = new Set(context.fullOutputItems);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return { fullOutputItems: next };
    }),
  },
}).createMachine({
  id: "trace",
  context: ({ input }) => ({
    trace: {
      items: [],
      isOpen: false,
      status: "complete",
      messageId: input.initialTraceId ?? undefined,
    },
    expandedItems: input.initialTraceId ? loadExpandedItems(input.initialTraceId) : new Set(),
    fullOutputItems: new Set(),
  }),
  on: {
    "TRACE.OPEN": { actions: "openTrace" },
    "TRACE.RESTORE": { actions: "restoreTrace" },
    "TRACE.CLOSE": { actions: "closeTrace" },
    "TRACE.UPDATE": { actions: "updateTrace" },
    "TRACE.TOGGLE_EXPANDED": { actions: "toggleExpanded" },
    "TRACE.TOGGLE_FULL_OUTPUT": { actions: "toggleFullOutput" },
    "PHOENIX.METADATA": { actions: "updatePhoenix" },
    "RUNTIME.METADATA": { actions: "updateRuntime" },
  },
});

export type { PhoenixMetadata, TraceContext, TraceEvent, TraceInput, TraceState };
