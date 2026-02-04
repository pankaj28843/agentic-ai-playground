import type { MouseEvent as ReactMouseEvent, ReactNode, TouchEvent as ReactTouchEvent } from "react";
import { useCallback, useEffect, useRef } from "react";

/* eslint-disable react-refresh/only-export-components */
import { createActorContext } from "@xstate/react";
import type { SnapshotFrom } from "xstate";

import { layoutMachine, SIDEBAR_LIMITS, TRACE_LIMITS } from "./layoutMachine";

type LayoutSnapshot = SnapshotFrom<typeof layoutMachine>;

type ResizeHandleProps = {
  onMouseDown: (event: ReactMouseEvent) => void;
  onTouchStart: (event: ReactTouchEvent) => void;
};

const STORAGE_KEYS = {
  sidebar: "playground-sidebar-width",
  trace: "playground-trace-width",
} as const;

const loadWidth = (key: string, defaultValue: number, min: number, max: number): number => {
  if (typeof window === "undefined") return defaultValue;
  try {
    const stored = localStorage.getItem(key);
    if (stored) {
      const value = Number.parseInt(stored, 10);
      if (!Number.isNaN(value) && value >= min && value <= max) {
        return value;
      }
    }
  } catch {
    // Ignore storage errors
  }
  return defaultValue;
};

const persistWidth = (key: string, value: number): void => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, String(value));
  } catch {
    // Ignore storage errors
  }
};

const LayoutActorContext = createActorContext(layoutMachine);

export const LayoutProvider = ({ children }: { children: ReactNode }) => {
  const initialSidebarWidth = loadWidth(
    STORAGE_KEYS.sidebar,
    SIDEBAR_LIMITS.defaultWidth,
    SIDEBAR_LIMITS.min,
    SIDEBAR_LIMITS.max,
  );
  const initialTraceWidth = loadWidth(
    STORAGE_KEYS.trace,
    TRACE_LIMITS.defaultWidth,
    TRACE_LIMITS.min,
    TRACE_LIMITS.max,
  );

  return (
    <LayoutActorContext.Provider
      logic={layoutMachine}
      options={{ input: { sidebarWidth: initialSidebarWidth, traceWidth: initialTraceWidth } }}
    >
      <LayoutGlobalListeners />
      {children}
    </LayoutActorContext.Provider>
  );
};

const LayoutGlobalListeners = () => {
  const actorRef = LayoutActorContext.useActorRef();
  const snapshot = LayoutActorContext.useSelector((state) => state);
  const { isResizing, sidebarWidth, traceWidth } = snapshot.context;
  const wasResizingRef = useRef(false);

  useEffect(() => {
    if (!isResizing) {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      return;
    }
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (event: globalThis.MouseEvent) => {
      event.preventDefault();
      actorRef.send({ type: "RESIZE.MOVE", clientX: event.clientX });
    };
    const onTouchMove = (event: globalThis.TouchEvent) => {
      if (event.touches.length === 1) {
        actorRef.send({ type: "RESIZE.MOVE", clientX: event.touches[0].clientX });
      }
    };
    const onEnd = () => {
      actorRef.send({ type: "RESIZE.END" });
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onEnd);
    document.addEventListener("touchmove", onTouchMove, { passive: false });
    document.addEventListener("touchend", onEnd);

    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onEnd);
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("touchend", onEnd);
    };
  }, [actorRef, isResizing]);

  useEffect(() => {
    if (wasResizingRef.current && !isResizing) {
      persistWidth(STORAGE_KEYS.sidebar, sidebarWidth);
      persistWidth(STORAGE_KEYS.trace, traceWidth);
    }
    wasResizingRef.current = isResizing;
  }, [isResizing, sidebarWidth, traceWidth]);

  return null;
};

export const useLayout = () => {
  const actorRef = LayoutActorContext.useActorRef();
  const snapshot = LayoutActorContext.useSelector((state) => state);
  const { sidebarWidth, traceWidth, isResizing } = snapshot.context;

  const startSidebarResize = useCallback(
    (clientX: number) => {
      actorRef.send({ type: "SIDEBAR.RESIZE.START", clientX });
    },
    [actorRef],
  );

  const startTraceResize = useCallback(
    (clientX: number) => {
      actorRef.send({ type: "TRACE.RESIZE.START", clientX });
    },
    [actorRef],
  );

  const sidebarResizeHandleProps: ResizeHandleProps = {
    onMouseDown: (event) => {
      event.preventDefault();
      startSidebarResize(event.clientX);
    },
    onTouchStart: (event) => {
      if (event.touches.length === 1) {
        startSidebarResize(event.touches[0].clientX);
      }
    },
  };

  const traceResizeHandleProps: ResizeHandleProps = {
    onMouseDown: (event) => {
      event.preventDefault();
      startTraceResize(event.clientX);
    },
    onTouchStart: (event) => {
      if (event.touches.length === 1) {
        startTraceResize(event.touches[0].clientX);
      }
    },
  };

  return {
    sidebarWidth,
    traceWidth,
    sidebarResizeHandleProps,
    traceResizeHandleProps,
    isResizing,
  };
};

export type { LayoutSnapshot };
