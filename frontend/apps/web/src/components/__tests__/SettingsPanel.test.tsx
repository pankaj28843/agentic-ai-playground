import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProfilesResponse } from "@agentic-ai-playground/api-client";
import { SettingsPanel } from "../SettingsPanel";

const setModelOverride = vi.fn();
const setToolGroupsOverride = vi.fn();
const setEnabledSkills = vi.fn();
const setEnabledPrompts = vi.fn();

vi.mock("../../contexts/SettingsContext", () => {
  return {
    useSettings: () => ({
      models: ["bedrock.nova-lite", "bedrock.nova-pro"],
      defaultModel: "bedrock.nova-lite",
      toolGroups: [
        { name: "techdocs", description: "Docs", tools: [], capabilities: [] },
        { name: "strands_basic", description: "Basic", tools: [], capabilities: [] },
      ],
      profileDefaults: [{ profileId: "quick", model: "bedrock.nova-lite", toolGroups: ["techdocs"] }],
      modelOverride: null,
      toolGroupsOverride: null,
      setModelOverride,
      setToolGroupsOverride,
      isLoading: false,
      error: null,
    }),
  };
});

vi.mock("../../contexts/ResourcesContext", () => {
  return {
    useResources: () => ({
      resources: {
        skills: [
          { name: "review", description: "", content: "", source: "" },
        ],
        prompts: [
          { name: "summarize", description: "", content: "", source: "" },
        ],
        diagnostics: { warnings: [] },
      },
      enabledSkills: ["review"],
      enabledPrompts: ["summarize"],
      setEnabledSkills,
      setEnabledPrompts,
    }),
  };
});

describe("SettingsPanel", () => {
  it("updates model override when selection changes", () => {
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

    render(<SettingsPanel profiles={profiles} runMode="quick" />);

    const select = screen.getByLabelText(/model override/i);
    fireEvent.change(select, { target: { value: "bedrock.nova-pro" } });
    expect(setModelOverride).toHaveBeenCalledWith("bedrock.nova-pro");
  });
});
