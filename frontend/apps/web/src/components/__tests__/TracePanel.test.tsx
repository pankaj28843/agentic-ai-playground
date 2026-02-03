import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TracePanel, type TraceItem } from "../TracePanel";

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

describe("TracePanel", () => {
  it("toggles full tool output", () => {
    const expanded = new Set([0]);
    render(
      <TracePanel
        items={items}
        isOpen
        onClose={() => undefined}
        expandedItems={expanded}
        onToggleExpanded={() => undefined}
      />
    );

    expect(screen.getByText(/short output/i)).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: /show full output/i });
    fireEvent.click(toggle);
    expect(screen.getByText(/full output/i)).toBeInTheDocument();
  });
});
