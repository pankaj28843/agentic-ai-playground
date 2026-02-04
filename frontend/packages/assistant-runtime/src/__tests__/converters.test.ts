import { describe, expect, it } from "vitest";

import type { ThreadMessage as ApiThreadMessage } from "@agentic-ai-playground/api-client";
import { toThreadMessage } from "../converters";

describe("toThreadMessage", () => {
  it("maps agent-event parts to data parts", () => {
    const apiMessage: ApiThreadMessage = {
      id: "msg-1",
      role: "assistant",
      content: [
        {
          type: "agent-event",
          agentName: "agent-1",
          eventType: "start",
        },
      ],
      createdAt: "2026-01-01T00:00:00Z",
    };

    const result = toThreadMessage(apiMessage);
    expect(result.content[0]).toEqual({
      type: "data",
      name: "agent-event",
      data: apiMessage.content[0],
    });
  });
});
