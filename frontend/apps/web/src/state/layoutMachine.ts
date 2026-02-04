import { assign, setup } from "xstate";

type LayoutContext = {
  sidebarWidth: number;
  traceWidth: number;
  isResizing: boolean;
  resizingTarget: "sidebar" | "trace" | null;
  startX: number;
  startWidth: number;
};

type LayoutInput = {
  sidebarWidth: number;
  traceWidth: number;
};

type LayoutEvent =
  | { type: "SIDEBAR.RESIZE.START"; clientX: number }
  | { type: "TRACE.RESIZE.START"; clientX: number }
  | { type: "RESIZE.MOVE"; clientX: number }
  | { type: "RESIZE.END" };

export const SIDEBAR_LIMITS = {
  min: 180,
  max: 400,
  defaultWidth: 260,
} as const;

export const TRACE_LIMITS = {
  min: 280,
  max: 600,
  defaultWidth: 380,
} as const;

export const layoutMachine = setup({
  types: {
    context: {} as LayoutContext,
    input: {} as LayoutInput,
    events: {} as LayoutEvent,
  },
  actions: {
    startSidebarResize: assign(({ context, event }) => ({
      isResizing: true,
      resizingTarget: "sidebar",
      startX: (event as { clientX: number }).clientX,
      startWidth: context.sidebarWidth,
    })),
    startTraceResize: assign(({ context, event }) => ({
      isResizing: true,
      resizingTarget: "trace",
      startX: (event as { clientX: number }).clientX,
      startWidth: context.traceWidth,
    })),
    updateResize: assign(({ context, event }) => {
      if (!context.resizingTarget) {
        return {};
      }
      const clientX = (event as { clientX: number }).clientX;
      const delta = clientX - context.startX;
      if (context.resizingTarget === "sidebar") {
        const nextWidth = Math.max(
          SIDEBAR_LIMITS.min,
          Math.min(SIDEBAR_LIMITS.max, context.startWidth + delta),
        );
        return { sidebarWidth: nextWidth };
      }
      const nextWidth = Math.max(
        TRACE_LIMITS.min,
        Math.min(TRACE_LIMITS.max, context.startWidth - delta),
      );
      return { traceWidth: nextWidth };
    }),
    endResize: assign({
      isResizing: false,
      resizingTarget: null,
      startX: 0,
      startWidth: 0,
    }),
  },
}).createMachine({
  id: "layout",
  initial: "idle",
  context: ({ input }) => ({
    sidebarWidth: input.sidebarWidth,
    traceWidth: input.traceWidth,
    isResizing: false,
    resizingTarget: null,
    startX: 0,
    startWidth: 0,
  }),
  states: {
    idle: {
      on: {
        "SIDEBAR.RESIZE.START": { target: "resizing", actions: "startSidebarResize" },
        "TRACE.RESIZE.START": { target: "resizing", actions: "startTraceResize" },
      },
    },
    resizing: {
      on: {
        "RESIZE.MOVE": { actions: "updateResize" },
        "RESIZE.END": { target: "idle", actions: "endResize" },
      },
    },
  },
});

export type { LayoutContext, LayoutEvent, LayoutInput };
