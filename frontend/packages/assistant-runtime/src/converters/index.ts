/**
 * Message converters for assistant-ui <-> API format transformation.
 *
 * These utilities handle the conversion between:
 * - ThreadMessage (assistant-ui internal format)
 * - ApiThreadMessage (backend API format)
 */

import type {
  ExportedMessageRepository,
  ThreadMessage,
  ThreadMessageLike,
} from "@assistant-ui/react";
import type { ThreadMessage as ApiThreadMessage, MessagePart } from "@agentic-ai-playground/api-client";

/**
 * Convert a ThreadMessage to the API format for persistence.
 */
export const toApiMessage = (message: ThreadMessage): ApiThreadMessage => {
  const content: MessagePart[] = [];
  for (const part of message.content) {
    if (part.type === "text") {
      content.push({ type: "text", text: part.text });
    } else if (part.type === "tool-call") {
      content.push({
        type: "tool-call",
        toolCallId: part.toolCallId,
        toolName: part.toolName,
        args: part.args,
        argsText: part.argsText,
        result: part.result,
        isError: part.isError,
      });
    } else if (part.type === "reasoning") {
      content.push({
        type: "reasoning",
        text: part.text,
      });
    }
  }
  return {
    id: message.id,
    role: message.role as "user" | "assistant" | "system" | "tool",
    content,
    createdAt: message.createdAt.toISOString(),
  };
};

/**
 * Convert an API message to ThreadMessageLike format for assistant-ui.
 */
export const toThreadMessage = (message: ApiThreadMessage): ThreadMessageLike => {
  const content: ThreadMessageLike["content"] = [];
  const parts = message.content;

  for (const part of parts) {
    if (part.type === "text" && typeof part.text === "string") {
      (content as Array<{ type: "text"; text: string }>).push({
        type: "text",
        text: part.text,
      });
    } else if (part.type === "tool-call" && typeof part.toolCallId === "string") {
      (
        content as Array<{
          type: "tool-call";
          toolCallId?: string;
          toolName: string;
          args?: unknown;
          argsText?: string;
          result?: unknown;
          isError?: boolean;
        }>
      ).push({
        type: "tool-call" as const,
        toolCallId: part.toolCallId as string,
        toolName: (part.toolName as string) ?? "unknown",
        args: part.args,
        argsText: part.argsText as string | undefined,
        result: part.result,
        isError: part.isError as boolean | undefined,
      });
    } else if (part.type === "reasoning" && typeof part.text === "string") {
      (content as Array<{ type: "reasoning"; text: string }>).push({
        type: "reasoning",
        text: part.text as string,
      });
    } else if (part.type === "agent-event") {
      (content as Array<{ type: "data"; name: string; data: unknown }>).push({
        type: "data",
        name: "agent-event",
        data: part,
      });
    }
  }

  return {
    id: message.id,
    role: message.role as "user" | "assistant" | "system",
    content,
    createdAt: new Date(message.createdAt),
    status: { type: "complete", reason: "stop" },
    metadata: {
      custom: {
        phoenixTraceId: message.phoenixTraceId,
        phoenixTraceUrl: message.phoenixTraceUrl,
        phoenixSessionId: message.phoenixSessionId,
        phoenixSessionUrl: message.phoenixSessionUrl,
        runProfile: message.runProfile,
        runMode: message.runMode,
        executionMode: message.executionMode,
        entrypointReference: message.entrypointReference,
        modelId: message.modelId,
        sessionEntryId: message.sessionEntryId,
      },
    },
  };
};

/**
 * Build an ExportedMessageRepository from a list of messages.
 */
export const buildRepository = (messages: ThreadMessageLike[]): ExportedMessageRepository => {
  return {
    headId: messages.at(-1)?.id ?? null,
    messages: messages.map((message, index) => ({
      message: message as ThreadMessage,
      parentId: index > 0 ? (messages[index - 1]?.id ?? null) : null,
    })),
  };
};
