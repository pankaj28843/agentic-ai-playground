import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, ProfilesResponse, ResourcesResponse, SettingsResponse } from "@agentic-ai-playground/api-client";
import { AppDataProvider } from "../../state/appDataContext";
import { OverridesProvider } from "../../state/overridesContext";
import { useSettings } from "../SettingsContext";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const SettingsProbe = () => {
  const { models, modelOverride, setModelOverride } = useSettings();
  return (
    <div>
      <div data-testid="models">{models.length}</div>
      <div data-testid="override">{modelOverride ?? "none"}</div>
      <button type="button" onClick={() => setModelOverride("override")}>set</button>
    </div>
  );
};

describe("SettingsContext", () => {
  it("exposes settings and overrides", async () => {
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
    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue(profiles),
      getSettings: vi.fn().mockResolvedValue(settings),
      listResources: vi.fn().mockResolvedValue(resources),
      getPhoenixConfig: vi.fn().mockResolvedValue({ enabled: false }),
      getThread: vi.fn(),
    } as unknown as ApiClient;

    render(
      <AppDataProvider apiClient={apiClient}>
        <OverridesProvider apiClient={apiClient} threadId={null}>
          <SettingsProbe />
        </OverridesProvider>
      </AppDataProvider>,
    );

    await flushPromises();

    expect(screen.getByTestId("models").textContent).toBe("1");
    screen.getByText("set").click();
    await waitFor(() => {
      expect(screen.getByTestId("override").textContent).toBe("override");
    });
  });
});
