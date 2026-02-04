import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { TraceProvider, useTrace } from "../TraceContext";

type PhoenixSubscriber = (metadata: { traceId?: string; sessionId?: string }) => void;

type RuntimeSubscriber = (metadata: { runMode?: string }) => void;

const subscribers = vi.hoisted(() => ({
  phoenix: [] as PhoenixSubscriber[],
  runtime: [] as RuntimeSubscriber[],
}));

vi.mock("@agentic-ai-playground/api-client", () => {
  subscribers.phoenix = [];
  subscribers.runtime = [];
  return {
    phoenixMetadataEvents: {
      subscribe: (cb: PhoenixSubscriber) => {
        subscribers.phoenix.push(cb);
        return () => {
          subscribers.phoenix = subscribers.phoenix.filter((item) => item !== cb);
        };
      },
    },
    runtimeMetadataEvents: {
      subscribe: (cb: RuntimeSubscriber) => {
        subscribers.runtime.push(cb);
        return () => {
          subscribers.runtime = subscribers.runtime.filter((item) => item !== cb);
        };
      },
    },
  };
});

const TraceProbe = () => {
  const { trace, openTrace, closeTrace, updateTrace, toggleItemExpanded, toggleItemOutput } =
    useTrace();
  return (
    <div>
      <div data-testid="open">{trace.isOpen ? "yes" : "no"}</div>
      <button
        type="button"
        onClick={() => openTrace({ items: [], status: "running", messageId: "msg-1" })}
      >
        open
      </button>
      <button type="button" onClick={closeTrace}>
        close
      </button>
      <button type="button" onClick={() => updateTrace({ status: "complete" })}>
        update
      </button>
      <button type="button" onClick={() => toggleItemExpanded(0)}>
        toggle-expanded
      </button>
      <button type="button" onClick={() => toggleItemOutput(0)}>
        toggle-output
      </button>
    </div>
  );
};

describe("TraceContext", () => {
  it("restores trace from URL and handles open/close", async () => {
    window.history.pushState({}, "", "/c/abc?trace_id=seed");
    render(
      <BrowserRouter>
        <TraceProvider>
          <TraceProbe />
        </TraceProvider>
      </BrowserRouter>,
    );

    expect(screen.getByTestId("open").textContent).toBe("yes");
    screen.getByText("open").click();
    expect(screen.getByTestId("open").textContent).toBe("yes");
    screen.getByText("update").click();
    screen.getByText("toggle-expanded").click();
    screen.getByText("toggle-output").click();
    screen.getByText("close").click();
    await waitFor(() => {
      expect(screen.getByTestId("open").textContent).toBe("no");
    });
  });

  it("propagates metadata events", () => {
    window.history.pushState({}, "", "/c/abc");
    render(
      <BrowserRouter>
        <TraceProvider>
          <TraceProbe />
        </TraceProvider>
      </BrowserRouter>,
    );

    subscribers.phoenix.forEach((cb) => cb({ traceId: "t" }));
    subscribers.runtime.forEach((cb) => cb({ runMode: "quick" }));

    expect(subscribers.phoenix.length).toBeGreaterThan(0);
    expect(subscribers.runtime.length).toBeGreaterThan(0);
  });
});
