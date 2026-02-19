import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, ProfilesResponse, PhoenixConfig } from "@agentic-ai-playground/api-client";
import { AppDataProvider, useAppDataSelector } from "../appDataContext";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const AppDataProbe = () => {
  const runMode = useAppDataSelector((state) => state.context.runMode);
  return (
    <div>
      <div data-testid="run-mode">{runMode}</div>
    </div>
  );
};

describe("AppDataProvider", () => {
  it("provides loaded data", async () => {
    const profiles: ProfilesResponse = {
      profiles: [{ id: "quick", name: "Quick", description: "", entrypointType: "single", entrypointReference: "general", default: true, metadata: {} }],
      runModes: ["quick"],
      defaultRunMode: "quick",
    };
    const phoenix: PhoenixConfig = { enabled: false };

    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue(profiles),
      getPhoenixConfig: vi.fn().mockResolvedValue(phoenix),
    } as unknown as ApiClient;

    render(
      <AppDataProvider apiClient={apiClient}>
        <AppDataProbe />
      </AppDataProvider>,
    );

    await flushPromises();

    expect(screen.getByTestId("run-mode").textContent).toBe("quick");
  });
});
