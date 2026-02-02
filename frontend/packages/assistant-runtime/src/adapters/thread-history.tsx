/**
 * Thread history adapter for loading and persisting messages.
 */

import type { ReactNode } from "react";
import { useMemo } from "react";
import {
  RuntimeAdapterProvider,
  useAssistantApi,
  type ThreadHistoryAdapter,
  type ThreadMessage,
} from "@assistant-ui/react";
import { phoenixMetadataEvents, runtimeMetadataEvents, type RuntimeMetadata } from "@agentic-ai-playground/api-client";
import { api } from "./chat-model";
import { buildRepository, toApiMessage, toThreadMessage } from "../converters";

// Track latest Phoenix trace ID from streaming for persistence
let latestPhoenixTraceId: string | undefined;
let latestPhoenixSessionId: string | undefined;
let latestRuntimeMetadata: RuntimeMetadata | undefined;

// Subscribe to Phoenix metadata to capture trace IDs
phoenixMetadataEvents.subscribe((metadata) => {
  if (metadata.traceId) {
    latestPhoenixTraceId = metadata.traceId;
  }
  if (metadata.sessionId) {
    latestPhoenixSessionId = metadata.sessionId;
  }
});

runtimeMetadataEvents.subscribe((metadata) => {
  latestRuntimeMetadata = {
    ...latestRuntimeMetadata,
    ...metadata,
  };
});

/**
 * Provider component that sets up the thread history adapter.
 */
export const ThreadAdapterProvider = ({ children }: { children?: ReactNode }) => {
  const threadApi = useAssistantApi();

  const history = useMemo<ThreadHistoryAdapter>(
    () => ({
      async load() {
        const { remoteId } = threadApi.threadListItem().getState();
        if (!remoteId) {
          return buildRepository([]);
        }
        const { messages } = await api.getMessages(remoteId);
        return buildRepository(messages.map(toThreadMessage));
      },

      async append(item: { message: ThreadMessage }) {
        const { remoteId } = await threadApi.threadListItem().initialize();
        // For assistant messages, include the Phoenix trace ID from the stream
        const traceId = item.message.role === "assistant" ? latestPhoenixTraceId : undefined;
        const runtimeMetadata = item.message.role === "assistant" ? latestRuntimeMetadata : undefined;
        await api.appendMessage(
          remoteId,
          toApiMessage(item.message),
          traceId,
          runtimeMetadata,
          latestPhoenixSessionId,
        );
        // Clear the captured metadata after saving to avoid reusing it
        if (traceId) {
          latestPhoenixTraceId = undefined;
        }
        if (latestPhoenixSessionId) {
          latestPhoenixSessionId = undefined;
        }
        if (runtimeMetadata) {
          latestRuntimeMetadata = undefined;
        }
      },
    }),
    [threadApi],
  );

  return <RuntimeAdapterProvider adapters={{ history }}>{children}</RuntimeAdapterProvider>;
};
