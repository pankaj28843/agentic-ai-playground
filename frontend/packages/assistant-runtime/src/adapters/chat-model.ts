/**
 * Chat model adapter for streaming responses from the backend.
 */

import type { ChatModelAdapter, ChatModelRunResult } from "@assistant-ui/react";
import { ApiClient, phoenixMetadataEvents, runtimeMetadataEvents } from "@agentic-ai-playground/api-client";
import type { RunOverrides } from "../types";
import { toApiMessage } from "../converters";
import { normalizeStreamPayload, parseStreamLine } from "../stream/normalize";

const baseUrl =
  (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ?? "";

const api = new ApiClient(baseUrl);

/**
 * Create a ChatModelAdapter for streaming responses from the backend.
 *
 * @param runMode - Public profile name (run mode)
 */
export const createChatAdapter = (
  getRunMode: () => string | undefined,
  getOverrides: () => RunOverrides | undefined,
): ChatModelAdapter => ({
  async *run({ messages, abortSignal, unstable_threadId }): AsyncGenerator<ChatModelRunResult> {
    const runMode = getRunMode();
    const overrides = getOverrides();
    const response = await api.runChat(
      {
        messages: messages.map(toApiMessage),
        threadId: unstable_threadId,
        runMode,
        modelOverride: overrides?.modelOverride ?? undefined,
        toolGroupsOverride: overrides?.toolGroupsOverride ?? undefined,
      },
      abortSignal,
    );

    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errorBody = await response.text();
        if (errorBody) {
          errorDetail = errorBody;
        }
      } catch {
        // Ignore errors reading response body
      }
      throw new Error(`Chat error: ${response.status} ${errorDetail}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const result = await reader.read();
      if (result.done) {
        break;
      }
      buffer += decoder.decode(result.value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const payload = parseStreamLine(line);
        if (!payload) {
          console.warn("Failed to parse stream line:", line);
          continue;
        }

        const normalized = normalizeStreamPayload(payload);
        if (normalized.phoenixMeta) {
          phoenixMetadataEvents.emit(normalized.phoenixMeta);
        }
        if (normalized.runtimeMeta) {
          runtimeMetadataEvents.emit(normalized.runtimeMeta);
        }
        if (normalized.content && normalized.content.length > 0) {
          yield { content: normalized.content as ChatModelRunResult["content"] };
        }
      }
    }
  },
});

export { api };
