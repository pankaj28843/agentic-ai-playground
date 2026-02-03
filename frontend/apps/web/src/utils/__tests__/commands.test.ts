import { describe, expect, it } from "vitest";

import type { ResourcesResponse } from "@agentic-ai-playground/api-client";
import { filterResources, parseCommand, resolveCommand } from "../commands";

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

describe("commands", () => {
  it("parses prompt command", () => {
    const parsed = parseCommand("/prompt summarize");
    expect(parsed).toEqual({ type: "prompt", query: "summarize" });
  });

  it("resolves prompt command", () => {
    const result = resolveCommand("/prompt summarize", resources, ["summarize"]);
    expect(result.applied).toBe(true);
    expect(result.resolvedText).toBe("Summarize content");
  });

  it("resolves skill command", () => {
    const result = resolveCommand("/skill review", resources, ["review"]);
    expect(result.applied).toBe(true);
    expect(result.resolvedText).toContain("Skill: review");
  });

  it("returns an error when resolved content is empty", () => {
    const emptyResources: ResourcesResponse = {
      skills: [],
      prompts: [
        {
          name: "empty",
          description: "Empty prompt",
          content: "   ",
          source: "global",
        },
      ],
      diagnostics: { warnings: [] },
    };
    const result = resolveCommand("/prompt empty", emptyResources, ["empty"]);
    expect(result.applied).toBe(false);
    expect(result.error).toMatch(/empty/);
  });

  it("filters resources by query", () => {
    const items = filterResources("prompt", resources, "sum", ["summarize"]);
    expect(items).toHaveLength(1);
    expect(items[0].name).toBe("summarize");
  });
});
