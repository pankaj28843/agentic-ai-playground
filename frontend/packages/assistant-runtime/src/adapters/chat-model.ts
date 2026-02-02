/**
 * Chat model adapter for streaming responses from the backend.
 */

import type { ChatModelAdapter, ChatModelRunResult } from "@assistant-ui/react";
import { ApiClient, phoenixMetadataEvents, runtimeMetadataEvents } from "@agentic-ai-playground/api-client";
import { toApiMessage } from "../converters";

const baseUrl =
  (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ?? "";

const api = new ApiClient(baseUrl);

// Content part types that assistant-ui natively supports for rendering
// Other types (like agent-event for multi-agent tracing) are filtered out
const ASSISTANT_UI_SUPPORTED_TYPES = new Set(["text", "tool-call", "reasoning"]);

/**
 * Create a ChatModelAdapter for streaming responses from the backend.
 *
 * @param runMode - Public profile name (run mode)
 */
export const createChatAdapter = (runMode?: string): ChatModelAdapter => ({
  async *run({ messages, abortSignal, unstable_threadId }): AsyncGenerator<ChatModelRunResult> {
    const response = await api.runChat(
      {
        messages: messages.map(toApiMessage),
        threadId: unstable_threadId,
        runMode,
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
        if (!line.trim()) {
          continue;
        }
        try {
          const payload = JSON.parse(line) as {
            content?: Array<{
              type: string;
              text?: string;
              toolName?: string;
              toolCallId?: string;
              args?: unknown;
              argsText?: string;
              result?: unknown;
              isError?: boolean;
            }>;
            text?: string;
            phoenixTraceId?: string;
            phoenixSessionId?: string;
            runMode?: string;
            profileName?: string;
            modelId?: string;
            executionMode?: string;
            entrypointReference?: string;
          };

          // Emit Phoenix metadata when received (usually on final chunk)
          if (payload.phoenixTraceId || payload.phoenixSessionId) {
            phoenixMetadataEvents.emit({
              traceId: payload.phoenixTraceId,
              sessionId: payload.phoenixSessionId,
            });
          }

          // Emit runtime metadata when received (on final chunk)
          if (
            payload.runMode ||
            payload.profileName ||
            payload.modelId ||
            payload.executionMode ||
            payload.entrypointReference
          ) {
            runtimeMetadataEvents.emit({
              runMode: payload.runMode,
              profileName: payload.profileName,
              modelId: payload.modelId,
              executionMode: payload.executionMode,
              entrypointReference: payload.entrypointReference,
            });
          }

          if (payload.content && Array.isArray(payload.content)) {
            // Filter to only types that assistant-ui supports
            // Note: agent-event types are filtered here but the backend still
            // tracks multi-agent events for future Phoenix/observability integration
            const supportedContent = payload.content.filter(
              (part) => ASSISTANT_UI_SUPPORTED_TYPES.has(part.type)
            );
            if (supportedContent.length > 0) {
              yield { content: supportedContent as ChatModelRunResult["content"] };
            }
          } else if (payload.text) {
            yield { content: [{ type: "text" as const, text: payload.text }] };
          }
        } catch {
          console.warn("Failed to parse stream line:", line);
        }
      }
    }
  },
});

export { api };
