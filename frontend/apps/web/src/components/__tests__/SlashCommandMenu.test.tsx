import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiClient, ResourcesResponse } from "@agentic-ai-playground/api-client";
import { AppDataProvider } from "../../state/appDataContext";
import { SlashCommandMenu } from "../SlashCommandMenu";

const resources: ResourcesResponse = {
  skills: [
    {
      name: "review",
      description: "Review instructions",
      content: "Review content",
      source: "global",
    },
  ],
  prompts: [
    {
      name: "summarize",
      description: "Summarize text",
      content: "Summarize content",
      source: "global",
    },
  ],
  diagnostics: { warnings: [] },
};

const composerApi = {
  setText: vi.fn(),
};

const mockState = {
  composer: { text: "/prompt" },
};

vi.mock("@assistant-ui/react", () => {
  return {
    useAssistantApi: () => ({ composer: () => composerApi }),
    useAssistantState: (selector: (state: typeof mockState) => unknown) => selector(mockState),
  };
});

describe("SlashCommandMenu", () => {
  it("renders prompt items and sets text on click", async () => {
    const apiClient = {
      listProfiles: vi.fn().mockResolvedValue({
        profiles: [],
        runModes: [],
        defaultRunMode: null,
      }),
      getSettings: vi.fn().mockResolvedValue({
        models: [],
        defaultModel: null,
        toolGroups: [],
        profileDefaults: [],
        inferenceProfiles: [],
        warnings: [],
      }),
      listResources: vi.fn().mockResolvedValue(resources),
      getPhoenixConfig: vi.fn().mockResolvedValue({ enabled: false }),
    } as unknown as ApiClient;

    render(
      <AppDataProvider apiClient={apiClient}>
        <SlashCommandMenu />
      </AppDataProvider>,
    );

    const item = await screen.findByRole("button", { name: /summarize/i });
    fireEvent.click(item);

    expect(composerApi.setText).toHaveBeenCalledWith("Summarize content");
  });
});
