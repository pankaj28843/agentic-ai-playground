import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ProfilesResponse } from "@agentic-ai-playground/api-client";
import { SettingsPanel } from "../SettingsPanel";

const setModelOverride = vi.fn();
const setToolGroupsOverride = vi.fn();
const setEnabledSkills = vi.fn();
const setEnabledPrompts = vi.fn();

const baseProfiles: ProfilesResponse = {
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

let mockSettingsState = {
  models: ["bedrock.nova-lite", "bedrock.nova-pro"],
  defaultModel: "bedrock.nova-lite",
  toolGroups: [
    { name: "techdocs", description: "Docs", tools: [], capabilities: [] },
    { name: "strands_basic", description: "Basic", tools: [], capabilities: [] },
  ],
  profileDefaults: [{ profileId: "quick", model: "bedrock.nova-lite", toolGroups: ["techdocs"] }],
  inferenceProfiles: [
    {
      inferenceProfileId: "profile-1",
      inferenceProfileArn: "arn:aws:bedrock:eu-central-1:123:inference-profile/profile-1",
      name: "Test Profile",
      status: "ACTIVE",
      type: "ON_DEMAND",
    },
  ],
  warnings: [] as string[],
  modelOverride: null as string | null,
  toolGroupsOverride: null as string[] | null,
  setModelOverride,
  setToolGroupsOverride,
  isLoading: false,
  error: null as string | null,
};

vi.mock("../../contexts/SettingsContext", () => {
  return {
    useSettings: () => mockSettingsState,
  };
});

vi.mock("../../contexts/ResourcesContext", () => {
  return {
    useResources: () => ({
      resources: {
        skills: [{ name: "review", description: "", content: "", source: "" }],
        prompts: [{ name: "summarize", description: "", content: "", source: "" }],
        warnings: [],
      },
      enabledSkills: ["review"],
      enabledPrompts: ["summarize"],
      setEnabledSkills,
      setEnabledPrompts,
    }),
  };
});

describe("SettingsPanel", () => {
  afterEach(() => {
    cleanup();
  });
  beforeEach(() => {
    setModelOverride.mockClear();
    setToolGroupsOverride.mockClear();
    setEnabledSkills.mockClear();
    setEnabledPrompts.mockClear();
    mockSettingsState = {
      ...mockSettingsState,
      warnings: [],
      modelOverride: null,
      toolGroupsOverride: null,
      isLoading: false,
      error: null,
    };
  });

  it("updates model override when selection changes", () => {
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);

    const select = screen.getByLabelText(/model override/i);
    fireEvent.change(select, { target: { value: "bedrock.nova-pro" } });
    expect(setModelOverride).toHaveBeenCalledWith("bedrock.nova-pro");
  });

  it("allows selecting inference profiles from the dropdown", () => {
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);

    const select = screen.getByLabelText(/model override/i);
    fireEvent.change(select, {
      target: {
        value: "arn:aws:bedrock:eu-central-1:123:inference-profile/profile-1",
      },
    });
    expect(setModelOverride).toHaveBeenCalledWith(
      "arn:aws:bedrock:eu-central-1:123:inference-profile/profile-1",
    );
  });

  it("warns when the override is not in the allowed list", () => {
    mockSettingsState.modelOverride = "custom.invalid";
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);

    expect(
      screen.getByText(/selected override is not in the allowed list/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /clear override/i }));
    expect(setModelOverride).toHaveBeenCalledWith(null);
  });

  it("shows tool override warning for multi-agent profiles", () => {
    mockSettingsState.toolGroupsOverride = ["techdocs"];
    const profiles: ProfilesResponse = {
      profiles: [
        {
          id: "graph",
          name: "Graph",
          description: "",
          entrypointType: "graph",
          entrypointReference: "default",
          default: true,
          metadata: {},
        },
      ],
      runModes: ["graph"],
      defaultRunMode: "graph",
    };

    render(<SettingsPanel profiles={profiles} runMode="graph" />);

    expect(
      screen.getByText(/tool overrides apply across all modes/i),
    ).toBeInTheDocument();
  });

  it("toggles tool overrides and applies select all/none", () => {
    const { rerender } = render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);

    const toggle = screen.getByLabelText(/override tool groups/i);
    fireEvent.click(toggle);
    expect(setToolGroupsOverride).toHaveBeenCalledWith(["techdocs", "strands_basic"]);

    mockSettingsState.toolGroupsOverride = ["techdocs", "strands_basic"];
    rerender(<SettingsPanel profiles={baseProfiles} runMode="quick" />);

    fireEvent.click(screen.getAllByRole("button", { name: /disable all/i })[0]);
    expect(setToolGroupsOverride).toHaveBeenCalledWith([]);

    fireEvent.click(screen.getAllByRole("button", { name: /enable all/i })[0]);
    expect(setToolGroupsOverride).toHaveBeenCalledWith(["techdocs", "strands_basic"]);
  });

  it("toggles skills and prompts", () => {
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);

    fireEvent.click(screen.getAllByRole("button", { name: /enable all/i })[0]);
    expect(setEnabledSkills).toHaveBeenCalledWith(["review"]);

    fireEvent.click(screen.getAllByRole("button", { name: /disable all/i })[0]);
    expect(setEnabledSkills).toHaveBeenCalledWith([]);

    fireEvent.click(screen.getAllByRole("button", { name: /enable all/i })[1]);
    expect(setEnabledPrompts).toHaveBeenCalledWith(["summarize"]);

    fireEvent.click(screen.getAllByRole("button", { name: /disable all/i })[1]);
    expect(setEnabledPrompts).toHaveBeenCalledWith([]);
  });

  it("shows loading and warning states", () => {
    mockSettingsState.isLoading = true;
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);
    expect(screen.getByText(/loading settings/i)).toBeInTheDocument();

    mockSettingsState.isLoading = false;
    mockSettingsState.warnings = ["Warning message"];
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);
    expect(screen.getByText("Warning message")).toBeInTheDocument();

    mockSettingsState.error = "Error";
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);
    expect(screen.getByText("Error")).toBeInTheDocument();
  });

  it("shows profile defaults when tool override disabled", () => {
    render(<SettingsPanel profiles={baseProfiles} runMode="quick" />);
    expect(screen.getByText(/using profile tool groups/i)).toBeInTheDocument();
  });
});
