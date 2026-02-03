import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ResourcesResponse } from "@agentic-ai-playground/api-client";
import { ResourcesProvider } from "../../contexts/ResourcesContext";
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
  it("renders prompt items and sets text on click", () => {
    render(
      <ResourcesProvider
        value={{
          resources,
          isLoading: false,
          error: null,
          enabledSkills: ["review"],
          enabledPrompts: ["summarize"],
          setEnabledSkills: () => undefined,
          setEnabledPrompts: () => undefined,
        }}
      >
        <SlashCommandMenu />
      </ResourcesProvider>,
    );

    const item = screen.getByRole("button", { name: /summarize/i });
    fireEvent.click(item);

    expect(composerApi.setText).toHaveBeenCalledWith("Summarize content");
  });
});
