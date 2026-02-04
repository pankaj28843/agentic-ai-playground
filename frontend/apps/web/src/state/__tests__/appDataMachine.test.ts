import { createActor } from "xstate";
import { describe, expect, it, vi } from "vitest";

import type {
  ApiClient,
  PhoenixConfig,
  ProfilesResponse,
  ResourcesResponse,
  SettingsResponse,
} from "@agentic-ai-playground/api-client";
import { appDataMachine } from "../appDataMachine";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const buildApiClient = (
  overrides: Partial<{
    listProfiles: unknown;
    getSettings: unknown;
    listResources: unknown;
    getPhoenixConfig: unknown;
  }> = {},
) => {
  const profiles: ProfilesResponse = {
    profiles: [
      {
        id: "quick",
        name: "Quick",
        description: "",
        entrypointType: "single",
        entrypointReference: "general",
        default: true,
        metadata: {},
      },
    ],
    runModes: ["quick"],
    defaultRunMode: "quick",
  };
  const settings: SettingsResponse = {
    models: ["bedrock.nova-lite"],
    defaultModel: "bedrock.nova-lite",
    toolGroups: [],
    profileDefaults: [],
    inferenceProfiles: [],
    warnings: [],
  };
  const resources: ResourcesResponse = {
    skills: [{ name: "skill", description: "", content: "", source: "" }],
    prompts: [{ name: "prompt", description: "", content: "", source: "" }],
    diagnostics: { warnings: [] },
  };
  const phoenix: PhoenixConfig = {
    enabled: true,
    baseUrl: "https://phoenix",
    projectName: "proj",
    projectId: "pid",
  };

  return {
    listProfiles: vi.fn().mockResolvedValue(overrides.listProfiles ?? profiles),
    getSettings: vi.fn().mockResolvedValue(overrides.getSettings ?? settings),
    listResources: vi.fn().mockResolvedValue(overrides.listResources ?? resources),
    getPhoenixConfig: vi.fn().mockResolvedValue(overrides.getPhoenixConfig ?? phoenix),
  } as unknown as ApiClient;
};

describe("appDataMachine", () => {
  it("loads profiles and sets default run mode", async () => {
    const apiClient = buildApiClient();
    const actor = createActor(appDataMachine, { input: { apiClient } });
    actor.start();

    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.profiles?.profiles).toHaveLength(1);
    expect(snapshot.context.runMode).toBe("quick");
    expect(snapshot.context.errors.profiles).toBeNull();
  });

  it("keeps existing run mode when profiles resolve", async () => {
    const apiClient = buildApiClient();
    const actor = createActor(appDataMachine, { input: { apiClient } });
    actor.start();
    actor.send({ type: "RUNMODE.SET", value: "custom" });

    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.runMode).toBe("custom");
  });

  it("initializes enabled resources from response", async () => {
    const apiClient = buildApiClient();
    const actor = createActor(appDataMachine, { input: { apiClient } });
    actor.start();

    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.enabledSkills).toEqual(["skill"]);
    expect(snapshot.context.enabledPrompts).toEqual(["prompt"]);
  });

  it("captures settings errors", async () => {
    const apiClient = buildApiClient({
      getSettings: Promise.reject(new Error("no settings")),
    });
    const actor = createActor(appDataMachine, { input: { apiClient } });
    actor.start();

    await flushPromises();

    const snapshot = actor.getSnapshot();
    expect(snapshot.context.settings).toBeNull();
    expect(snapshot.context.errors.settings).toBe("no settings");
  });
});
