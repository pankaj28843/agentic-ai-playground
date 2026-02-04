import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { useResizableSidebar } from "../../hooks";
import { LayoutProvider } from "../layoutContext";

const LayoutProbe = () => {
  const {
    sidebarWidth,
    traceWidth,
    sidebarResizeHandleProps,
    traceResizeHandleProps,
    isResizing,
  } = useResizableSidebar();

  return (
    <div>
      <div data-testid="sidebar-width">{sidebarWidth}</div>
      <div data-testid="trace-width">{traceWidth}</div>
      <div data-testid="is-resizing">{isResizing ? "yes" : "no"}</div>
      <button data-testid="sidebar-handle" type="button" {...sidebarResizeHandleProps} />
      <button data-testid="trace-handle" type="button" {...traceResizeHandleProps} />
    </div>
  );
};

describe("LayoutProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    cleanup();
  });
  it("persists widths on resize end", () => {
    localStorage.setItem("playground-sidebar-width", "260");
    localStorage.setItem("playground-trace-width", "380");

    render(
      <LayoutProvider>
        <LayoutProbe />
      </LayoutProvider>,
    );

    const sidebarHandle = screen.getByTestId("sidebar-handle");
    fireEvent.mouseDown(sidebarHandle, { clientX: 100 });
    fireEvent.mouseMove(document, { clientX: 120 });
    fireEvent.mouseUp(document);

    const storedSidebar = Number.parseInt(
      localStorage.getItem("playground-sidebar-width") ?? "0",
      10,
    );
    expect(storedSidebar).not.toBe(0);

    const traceHandle = screen.getByTestId("trace-handle");
    fireEvent.mouseDown(traceHandle, { clientX: 200 });
    fireEvent.mouseMove(document, { clientX: 180 });
    fireEvent.mouseUp(document);

    const storedTrace = Number.parseInt(
      localStorage.getItem("playground-trace-width") ?? "0",
      10,
    );
    expect(storedTrace).not.toBe(0);
  });

  it("falls back to defaults for invalid storage", () => {
    localStorage.setItem("playground-sidebar-width", "9999");
    localStorage.setItem("playground-trace-width", "-1");

    render(
      <LayoutProvider>
        <LayoutProbe />
      </LayoutProvider>,
    );

    const sidebarWidth = Number.parseInt(
      screen.getAllByTestId("sidebar-width")[0].textContent ?? "0",
      10,
    );
    const traceWidth = Number.parseInt(
      screen.getAllByTestId("trace-width")[0].textContent ?? "0",
      10,
    );

    expect(sidebarWidth).toBe(260);
    expect(traceWidth).toBe(380);
  });
});
