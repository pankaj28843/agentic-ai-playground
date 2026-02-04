import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, ProfilesResponse, ResourcesResponse, SettingsResponse, PhoenixConfig } from "@agentic-ai-playground/api-client";
import { AppDataProvider, useAppDataSelector } from "../appDataContext";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const AppDataProbe = () => {
  const runMode = useAppDataSelector((state) => state.context.runMode);
  const modelCount = useAppDataSelector((state) => state.context.settings?.models.length ?? 0);
  return (
    <div>
      <div data-testid="run-mode">{runMode}</div>
      <div data-testid="models">{modelCount}</div>
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
    const settings: SettingsResponse = {
      models: ["m"],
      defaultModel: "m",
      toolGroups: [],
      profileDefaults: [],
      inferenceProfiles: [],
      warnings: [],
    };
    const resources: ResourcesResponse = {
      skills: [],
      prompts: [],
      diagnostics: { warnings: [] },
    };
    const phoenix: PhoenixConfig = { enabled: false };

    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue(profiles),
      getSettings: vi.fn().mockResolvedValue(settings),
      listResources: vi.fn().mockResolvedValue(resources),
      getPhoenixConfig: vi.fn().mockResolvedValue(phoenix),
    } as unknown as ApiClient;

    render(
      <AppDataProvider apiClient={apiClient}>
        <AppDataProbe />
      </AppDataProvider>,
    );

    await flushPromises();

    expect(screen.getByTestId("run-mode").textContent).toBe("quick");
    expect(screen.getByTestId("models").textContent).toBe("1");
  });
});
