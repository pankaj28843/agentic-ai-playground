import { createActor } from "xstate";
import { describe, expect, it, vi } from "vitest";

import type {
  ApiClient,
  PhoenixConfig,
  ProfilesResponse,
} from "@agentic-ai-playground/api-client";
import { appDataMachine } from "../appDataMachine";

const flushPromises = async () => new Promise((resolve) => setTimeout(resolve, 0));

const buildApiClient = (
  overrides: Partial<{
    listProfiles: unknown;
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
  const phoenix: PhoenixConfig = {
    enabled: true,
    baseUrl: "https://phoenix",
    projectName: "proj",
    projectId: "pid",
  };

  return {
    listProfiles: vi.fn().mockResolvedValue(overrides.listProfiles ?? profiles),
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
});
