import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, ProfilesResponse, ResourcesResponse, SettingsResponse } from "@agentic-ai-playground/api-client";
import { AppDataProvider } from "../../state/appDataContext";
import { useResources } from "../ResourcesContext";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const ResourcesProbe = () => {
  const { enabledSkills, setEnabledSkills } = useResources();
  return (
    <div>
      <div data-testid="skills">{enabledSkills.join(",")}</div>
      <button type="button" onClick={() => setEnabledSkills(["skill-a"])}>set</button>
    </div>
  );
};

describe("ResourcesContext", () => {
  it("exposes enabled resources", async () => {
    const profiles: ProfilesResponse = {
      profiles: [],
      runModes: [],
      defaultRunMode: null,
    };
    const settings: SettingsResponse = {
      models: [],
      defaultModel: null,
      toolGroups: [],
      profileDefaults: [],
      inferenceProfiles: [],
      warnings: [],
    };
    const resources: ResourcesResponse = {
      skills: [{ name: "skill", description: "", content: "", source: "" }],
      prompts: [],
      diagnostics: { warnings: [] },
    };
    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue(profiles),
      getSettings: vi.fn().mockResolvedValue(settings),
      listResources: vi.fn().mockResolvedValue(resources),
      getPhoenixConfig: vi.fn().mockResolvedValue({ enabled: false }),
    } as unknown as ApiClient;

    render(
      <AppDataProvider apiClient={apiClient}>
        <ResourcesProbe />
      </AppDataProvider>,
    );

    await flushPromises();

    expect(screen.getByTestId("skills").textContent).toBe("skill");
    screen.getByText("set").click();
    await waitFor(() => {
      expect(screen.getByTestId("skills").textContent).toBe("skill-a");
    });
  });
});
