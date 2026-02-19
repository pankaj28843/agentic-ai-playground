import { describe, expect, it, vi } from "vitest";

import { api, createChatAdapter } from "../adapters/chat-model";

const buildReader = (payload: string) => {
  const encoder = new TextEncoder();
  const chunks = [encoder.encode(payload)];
  let index = 0;
  return {
    read: vi.fn().mockImplementation(() => {
      if (index < chunks.length) {
        const value = chunks[index];
        index += 1;
        return Promise.resolve({ done: false, value });
      }
      return Promise.resolve({ done: true, value: undefined });
    }),
  };
};

describe("createChatAdapter", () => {
  it("uses latest run mode and maps agent events to data parts", async () => {
    let runMode = "quick";

    const adapter = createChatAdapter(() => runMode);

    const payload =
      JSON.stringify({
        content: [
          {
            type: "agent-event",
            agentName: "agent-1",
            eventType: "start",
          },
          {
            type: "tool-call",
            toolCallId: "call-1",
            toolName: "tool",
            argsText: "{\"q\":\"value\"}",
          },
        ],
      }) + "\n";

    const reader = buildReader(payload);
    const response = {
      ok: true,
      body: {
        getReader: () => reader,
      },
    } as Response;

    const runChat = vi.spyOn(api, "runChat").mockResolvedValue(response);

    const chunks = [] as Array<{ content: Array<{ type: string; name?: string; args?: unknown }> }>;
    for await (const chunk of adapter.run({ messages: [], abortSignal: undefined, unstable_threadId: "t1" })) {
      chunks.push(chunk as { content: Array<{ type: string; name?: string }> });
    }

    expect(runChat).toHaveBeenCalledWith(
      {
        messages: [],
        threadId: "t1",
        runMode: "quick",
      },
      undefined,
    );

    expect(chunks[0]?.content[0]?.type).toBe("data");
    expect(chunks[0]?.content[0]?.name).toBe("agent-event");
    const toolPart = chunks[0]?.content.find((part) => part.type === "tool-call");
    expect(toolPart?.args).toEqual({ q: "value" });

    runMode = "graph";

    await adapter.run({ messages: [], abortSignal: undefined, unstable_threadId: "t2" }).next();

    expect(runChat).toHaveBeenLastCalledWith(
      {
        messages: [],
        threadId: "t2",
        runMode: "graph",
      },
      undefined,
    );
  });
});
