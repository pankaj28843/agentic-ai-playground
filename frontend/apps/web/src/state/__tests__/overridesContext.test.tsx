import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@agentic-ai-playground/api-client";
import { OverridesProvider } from "../overridesContext";
import { useOverrides } from "../useOverrides";

const OverridesProbe = () => {
  const { modelOverride, setModelOverride } = useOverrides();
  return (
    <div>
      <div data-testid="model">{modelOverride ?? "none"}</div>
      <button type="button" onClick={() => setModelOverride("override")}>set</button>
    </div>
  );
};

describe("OverridesProvider", () => {
  it("syncs stored overrides and updates", async () => {
    localStorage.setItem(
      "playground-run-overrides-v1",
      JSON.stringify({ modelOverride: "stored", toolGroupsOverride: null }),
    );
    const apiClient = { getThread: vi.fn() } as unknown as ApiClient;

    render(
      <OverridesProvider apiClient={apiClient} threadId={null}>
        <OverridesProbe />
      </OverridesProvider>,
    );

    expect(screen.getByTestId("model").textContent).toBe("stored");
    screen.getByText("set").click();
    await waitFor(() => {
      expect(screen.getByTestId("model").textContent).toBe("override");
    });
  });
});
