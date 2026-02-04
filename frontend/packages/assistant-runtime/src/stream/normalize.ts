/**
 * Stream normalization helpers for assistant runtime adapters.
 *
 * Keeps streaming parsing logic in one place to reduce UI duplication and
 * ensure consistent handling of trace metadata and content parts.
 */

import type { ChatModelRunResult } from "@assistant-ui/react";
import type { RuntimeMetadata, PhoenixMetadata } from "../types";

export type StreamPayload = {
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

export type NormalizedStreamChunk = {
  content?: ChatModelRunResult["content"];
  phoenixMeta?: PhoenixMetadata;
  runtimeMeta?: RuntimeMetadata;
};

const SUPPORTED_TYPES = new Set(["text", "tool-call", "reasoning", "data"]);

const parseArgs = (argsText?: string, args?: unknown) => {
  if (argsText && (args === undefined || args === null)) {
    try {
      return JSON.parse(argsText);
    } catch {
      return { _raw: argsText };
    }
  }
  return args;
};

export const parseStreamLine = (line: string): StreamPayload | null => {
  if (!line.trim()) {
    return null;
  }
  try {
    return JSON.parse(line) as StreamPayload;
  } catch {
    return null;
  }
};

const normalizeContent = (content: StreamPayload["content"]): ChatModelRunResult["content"] => {
  if (!content) {
    return [];
  }

  const mapped = content.map((part) => {
    if (part.type === "agent-event") {
      return {
        type: "data",
        name: "agent-event",
        data: part,
      };
    }
    if (part.type === "tool-call") {
      return {
        ...part,
        args: parseArgs(part.argsText, part.args),
      };
    }
    return part;
  });

  return mapped.filter((part) => SUPPORTED_TYPES.has(part.type)) as ChatModelRunResult["content"];
};

export const normalizeStreamPayload = (payload: StreamPayload): NormalizedStreamChunk => {
  const chunk: NormalizedStreamChunk = {};

  if (payload.phoenixTraceId || payload.phoenixSessionId) {
    chunk.phoenixMeta = {
      traceId: payload.phoenixTraceId,
      sessionId: payload.phoenixSessionId,
    };
  }

  if (
    payload.runMode ||
    payload.profileName ||
    payload.modelId ||
    payload.executionMode ||
    payload.entrypointReference
  ) {
    chunk.runtimeMeta = {
      runMode: payload.runMode,
      profileName: payload.profileName,
      modelId: payload.modelId,
      executionMode: payload.executionMode,
      entrypointReference: payload.entrypointReference,
    };
  }

  if (payload.content && Array.isArray(payload.content)) {
    chunk.content = normalizeContent(payload.content);
  } else if (payload.text) {
    chunk.content = [{ type: "text", text: payload.text }];
  }

  return chunk;
};
