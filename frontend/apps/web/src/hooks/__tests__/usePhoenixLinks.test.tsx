import type { ReactNode } from "react";

import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, ProfilesResponse, ResourcesResponse, SettingsResponse } from "@agentic-ai-playground/api-client";
import { AppDataProvider } from "../../state/appDataContext";
import { usePhoenixLinks } from "../usePhoenixLinks";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

describe("usePhoenixLinks", () => {
  it("builds phoenix URLs", async () => {
    const profiles: ProfilesResponse = { profiles: [], runModes: [], defaultRunMode: null };
    const settings: SettingsResponse = {
      models: [],
      defaultModel: null,
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
      getPhoenixConfig: vi.fn().mockResolvedValue({
        enabled: true,
        baseUrl: "https://phoenix",
        projectId: "proj",
      }),
    } as unknown as ApiClient;

    const wrapper = ({ children }: { children: ReactNode }) => (
      <AppDataProvider apiClient={apiClient}>{children}</AppDataProvider>
    );

    const { result } = renderHook(() => usePhoenixLinks("trace-1", "sess-1"), { wrapper });

    await flushPromises();

    expect(result.current.enabled).toBe(true);
    expect(result.current.traceUrl).toContain("projects/proj/traces/");
    expect(result.current.sessionUrl).toBe(
      "https://phoenix/projects/proj/sessions?sessionId=sess-1",
    );
  });
});
