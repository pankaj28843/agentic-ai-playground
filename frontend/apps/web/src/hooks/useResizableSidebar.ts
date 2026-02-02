import { useCallback, useEffect, useRef, useState } from "react";

const STORAGE_KEY = "playground-sidebar-width";
const DEFAULT_SIDEBAR_WIDTH = 260;
const MIN_SIDEBAR_WIDTH = 180;
const MAX_SIDEBAR_WIDTH = 400;

const TRACE_STORAGE_KEY = "playground-trace-width";
const DEFAULT_TRACE_WIDTH = 380;
const MIN_TRACE_WIDTH = 280;
const MAX_TRACE_WIDTH = 600;

interface UseResizableSidebarResult {
  sidebarWidth: number;
  traceWidth: number;
  sidebarResizeHandleProps: {
    onMouseDown: (e: React.MouseEvent) => void;
    onTouchStart: (e: React.TouchEvent) => void;
  };
  traceResizeHandleProps: {
    onMouseDown: (e: React.MouseEvent) => void;
    onTouchStart: (e: React.TouchEvent) => void;
  };
  isResizing: boolean;
}

/**
 * Load width from localStorage with validation
 */
function loadWidth(key: string, defaultValue: number, min: number, max: number): number {
  if (typeof window === "undefined") return defaultValue;
  try {
    const stored = localStorage.getItem(key);
    if (stored) {
      const value = parseInt(stored, 10);
      if (!Number.isNaN(value) && value >= min && value <= max) {
        return value;
      }
    }
  } catch {
    // Ignore storage errors
  }
  return defaultValue;
}

/**
 * Save width to localStorage
 */
function saveWidth(key: string, value: number): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, String(value));
  } catch {
    // Ignore storage errors
  }
}

/**
 * Hook for managing resizable sidebar and trace panel widths
 * Stores pixel widths in localStorage for persistence
 */
export function useResizableSidebar(): UseResizableSidebarResult {
  const [sidebarWidth, setSidebarWidth] = useState(() =>
    loadWidth(STORAGE_KEY, DEFAULT_SIDEBAR_WIDTH, MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH)
  );
  const [traceWidth, setTraceWidth] = useState(() =>
    loadWidth(TRACE_STORAGE_KEY, DEFAULT_TRACE_WIDTH, MIN_TRACE_WIDTH, MAX_TRACE_WIDTH)
  );
  const [isResizing, setIsResizing] = useState(false);

  // Track which panel is being resized
  const resizingRef = useRef<"sidebar" | "trace" | null>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  // Handle mouse/touch move during resize
  const handleMove = useCallback((clientX: number) => {
    if (!resizingRef.current) return;

    const delta = clientX - startXRef.current;

    if (resizingRef.current === "sidebar") {
      // Sidebar: dragging right increases width
      const newWidth = Math.max(
        MIN_SIDEBAR_WIDTH,
        Math.min(MAX_SIDEBAR_WIDTH, startWidthRef.current + delta)
      );
      setSidebarWidth(newWidth);
    } else {
      // Trace panel: dragging left increases width (handle is on the left edge)
      const newWidth = Math.max(
        MIN_TRACE_WIDTH,
        Math.min(MAX_TRACE_WIDTH, startWidthRef.current - delta)
      );
      setTraceWidth(newWidth);
    }
  }, []);

  // Handle mouse/touch end
  const handleEnd = useCallback(() => {
    if (resizingRef.current === "sidebar") {
      setSidebarWidth((w) => {
        saveWidth(STORAGE_KEY, w);
        return w;
      });
    } else if (resizingRef.current === "trace") {
      setTraceWidth((w) => {
        saveWidth(TRACE_STORAGE_KEY, w);
        return w;
      });
    }
    resizingRef.current = null;
    setIsResizing(false);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  // Set up global event listeners when resizing
  useEffect(() => {
    if (!isResizing) return;

    const onMouseMove = (e: MouseEvent) => {
      e.preventDefault();
      handleMove(e.clientX);
    };

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1) {
        handleMove(e.touches[0].clientX);
      }
    };

    const onEnd = () => handleEnd();

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
  }, [isResizing, handleMove, handleEnd]);

  // Start resizing sidebar
  const startSidebarResize = useCallback((clientX: number) => {
    resizingRef.current = "sidebar";
    startXRef.current = clientX;
    startWidthRef.current = sidebarWidth;
    setIsResizing(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [sidebarWidth]);

  // Start resizing trace panel
  const startTraceResize = useCallback((clientX: number) => {
    resizingRef.current = "trace";
    startXRef.current = clientX;
    startWidthRef.current = traceWidth;
    setIsResizing(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, [traceWidth]);

  const sidebarResizeHandleProps = {
    onMouseDown: (e: React.MouseEvent) => {
      e.preventDefault();
      startSidebarResize(e.clientX);
    },
    onTouchStart: (e: React.TouchEvent) => {
      if (e.touches.length === 1) {
        startSidebarResize(e.touches[0].clientX);
      }
    },
  };

  const traceResizeHandleProps = {
    onMouseDown: (e: React.MouseEvent) => {
      e.preventDefault();
      startTraceResize(e.clientX);
    },
    onTouchStart: (e: React.TouchEvent) => {
      if (e.touches.length === 1) {
        startTraceResize(e.touches[0].clientX);
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
}
