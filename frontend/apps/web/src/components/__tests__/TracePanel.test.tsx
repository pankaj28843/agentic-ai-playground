import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useState } from "react";

import { TraceIndicator, TracePanel, type TraceItem } from "../TracePanel";

const baseProps = {
  isOpen: true,
  onClose: () => undefined,
  expandedItems: new Set<number>(),
  onToggleExpanded: () => undefined,
  fullOutputItems: new Set<number>(),
  onToggleFullOutput: () => undefined,
};

describe("TracePanel", () => {
  afterEach(() => {
    cleanup();
  });
  it("renders empty state and handles closed panel", () => {
    const { rerender } = render(
      <TracePanel items={[]} {...baseProps} />,
    );
    expect(screen.getByText(/no trace data yet/i)).toBeInTheDocument();

    rerender(<TracePanel items={[]} {...baseProps} isOpen={false} />);
    expect(screen.queryByText(/no trace data yet/i)).not.toBeInTheDocument();
  });

  it("builds phoenix links from fallback metadata", () => {
    render(
      <TracePanel
        items={[]}
        isOpen
        onClose={() => undefined}
        expandedItems={new Set()}
        onToggleExpanded={() => undefined}
        fullOutputItems={new Set()}
        onToggleFullOutput={() => undefined}
        phoenix={{
          phoenixBaseUrl: "https://phoenix.example",
          traceId: "trace-1",
          sessionId: "session-1",
          projectId: "project-1",
        }}
      />,
    );

    expect(screen.getAllByText(/view in phoenix/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/session history/i)).toBeInTheDocument();
  });

  it("toggles full tool output", () => {
    const items: TraceItem[] = [
      {
        type: "tool-call",
        toolName: "shell",
        args: { command: "ls" },
        result: "short output",
        resultFull: "full output",
        resultTruncated: true,
        status: "complete",
        timestamp: new Date().toISOString(),
      },
    ];

    const Wrapper = () => {
      const [fullOutputItems, setFullOutputItems] = useState(new Set<number>());
      return (
        <TracePanel
          items={items}
          isOpen
          onClose={() => undefined}
          expandedItems={new Set([0])}
          onToggleExpanded={() => undefined}
          fullOutputItems={fullOutputItems}
          onToggleFullOutput={(index) =>
            setFullOutputItems((prev) => {
              const next = new Set(prev);
              if (next.has(index)) {
                next.delete(index);
              } else {
                next.add(index);
              }
              return next;
            })
          }
        />
      );
    };

    render(<Wrapper />);

    expect(screen.getByText(/short output/i)).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: /show full output/i });
    fireEvent.click(toggle);
    expect(screen.getByText(/full output/i)).toBeInTheDocument();
  });

  it("renders thinking, agent events, and tool calls", () => {
    const startTime = new Date().toISOString();
    const items: TraceItem[] = [
      {
        type: "thinking",
        text: "Reasoning",
        timestamp: new Date(Date.now() + 1000).toISOString(),
      },
      {
        type: "thinking",
        text: "Early",
        timestamp: new Date(Date.now() - 1000).toISOString(),
      },
      {
        type: "thinking",
        text: "No time",
      },
      {
        type: "thinking",
        text: "Bad time",
        timestamp: "invalid",
      },
      {
        type: "agent-event",
        agentName: "Planner",
        eventType: "handoff",
        fromAgents: ["Planner"],
        toAgents: ["Worker"],
        handoffMessage: "Take over",
        timestamp: new Date(Date.now() + 1500).toISOString(),
      },
      {
        type: "agent-event",
        agentName: "Reviewer",
        eventType: "start",
        timestamp: new Date(Date.now() + 1600).toISOString(),
      },
      {
        type: "agent-event",
        agentName: "Reviewer",
        eventType: "complete",
        timestamp: new Date(Date.now() + 1700).toISOString(),
      },
      {
        type: "tool-call",
        toolName: "techdocs_search",
        args: { query: "XState" },
        result: '[{"text":"{\\"ok\\":true}"}]',
        resultFull: '[{"text":"{\\"ok\\":true,\\"more\\":1}"}]',
        resultTruncated: true,
        status: "complete",
        timestamp: new Date(Date.now() + 2000).toISOString(),
        callingAgent: "planner",
      },
      {
        type: "tool-call",
        toolName: "another",
        args: { raw: "{invalid" },
        result: "not-json\\nvalue",
        status: "error",
        timestamp: new Date(Date.now() + 2500).toISOString(),
        isError: true,
      },
      {
        type: "tool-call",
        toolName: "json",
        args: { ok: true },
        result: { ok: true },
        status: "complete",
        timestamp: new Date(Date.now() + 2600).toISOString(),
      },
      {
        type: "tool-call",
        toolName: "multi",
        args: { ok: true },
        result: '[{"text":"one"},{"text":"two"}]',
        status: "complete",
        timestamp: new Date(Date.now() + 2700).toISOString(),
      },
      {
        type: "tool-call",
        toolName: "nontxt",
        args: { ok: true },
        result: '[{"value":1}]',
        status: "complete",
        timestamp: new Date(Date.now() + 2800).toISOString(),
      },
      {
        type: "tool-call",
        toolName: "null",
        args: { ok: true },
        result: null,
        status: "complete",
        timestamp: new Date(Date.now() + 2900).toISOString(),
      },
      {
        type: "tool-call",
        toolName: "empty",
        args: { ok: true },
        status: "complete",
        timestamp: new Date(Date.now() + 3000).toISOString(),
      },
    ];

    render(
      <TracePanel
        items={items}
        isOpen
        onClose={() => undefined}
        status="running"
        startTime={startTime}
        expandedItems={new Set([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])}
        onToggleExpanded={() => undefined}
        fullOutputItems={new Set([2])}
        onToggleFullOutput={() => undefined}
        phoenix={{ traceUrl: "https://example.com", sessionUrl: "https://example.com/s" }}
        runtime={{ runMode: "swarm", modelId: "bedrock", executionMode: "auto", entrypointReference: "main" }}
      />,
    );

    expect(screen.getAllByText(/thinking/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/handoff/i)).toBeInTheDocument();
    expect(screen.getByText(/techdocs_search/i)).toBeInTheDocument();
    expect(screen.getByText(/another/i)).toBeInTheDocument();
    expect(screen.getByText(/view in phoenix/i)).toBeInTheDocument();
    expect(screen.getByText(/mode:/i)).toBeInTheDocument();
    expect(screen.getByText(/execution:/i)).toBeInTheDocument();
  });

  it("renders trace indicator when there are steps", () => {
    const { rerender } = render(
      <TraceIndicator
        thinkingCount={0}
        toolCallCount={0}
        agentEventCount={0}
        onClick={() => undefined}
      />,
    );
    expect(screen.queryByLabelText(/view agent trace/i)).not.toBeInTheDocument();

    rerender(
      <TraceIndicator
        thinkingCount={1}
        toolCallCount={1}
        agentEventCount={0}
        onClick={() => undefined}
        isRunning
      />,
    );
    expect(screen.getByLabelText(/view agent trace/i)).toBeInTheDocument();
    expect(screen.getByText(/live trace/i)).toBeInTheDocument();

    rerender(
      <TraceIndicator
        thinkingCount={1}
        toolCallCount={0}
        agentEventCount={0}
        onClick={() => undefined}
      />,
    );
    expect(screen.getByText(/1 step/i)).toBeInTheDocument();
  });
});
