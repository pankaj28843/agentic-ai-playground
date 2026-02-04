import { assign, setup } from "xstate";

import type { ResourcesResponse } from "@agentic-ai-playground/api-client";

import { parseCommand, resolveCommand } from "../utils/commands";

type QueueMode = "steer" | "follow-up";

type QueueItem = {
  text: string;
  mode: QueueMode;
};

type CommandResolution = {
  resolvedText: string;
  applied: boolean;
  error?: string;
};

type QueueContext = {
  queue: QueueItem[];
  warning: string | null;
  pendingSend: QueueItem | null;
  pendingReset: boolean;
  cancelRequested: boolean;
  wasRunning: boolean;
};

type QueueInput = {
  initialQueue?: QueueItem[];
};

type QueueEvent =
  | {
      type: "QUEUE.REQUEST";
      mode: QueueMode;
      composerText: string;
      attachmentCount: number;
      resources: ResourcesResponse | null;
      enabledSkills: string[];
      enabledPrompts: string[];
    }
  | {
      type: "SEND.REQUEST";
      composerText: string;
      attachmentCount: number;
      resources: ResourcesResponse | null;
      enabledSkills: string[];
      enabledPrompts: string[];
    }
  | { type: "ASSISTANT.RUNNING.CHANGED"; isRunning: boolean }
  | { type: "SEND.DISPATCHED" }
  | { type: "RESET.ACK" }
  | { type: "CANCEL.ACK" };

const resolveComposerText = (
  composerText: string,
  resources: ResourcesResponse | null,
  enabledSkills: string[],
  enabledPrompts: string[],
): CommandResolution => {
  const parsed = parseCommand(composerText);
  const enabled = parsed?.type === "prompt" ? enabledPrompts : enabledSkills;
  return resolveCommand(composerText, resources, enabled);
};

export const composerQueueMachine = setup({
  types: {
    context: {} as QueueContext,
    input: {} as QueueInput,
    events: {} as QueueEvent,
  },
  actions: {
    enqueueMessage: assign(({ context, event }) => {
      const params = event as Extract<QueueEvent, { type: "QUEUE.REQUEST" }>;
      if (!params.composerText && params.attachmentCount === 0) {
        return { warning: null };
      }
      if (params.attachmentCount > 0) {
        return { warning: "Attachments cannot be queued yet." };
      }
      const resolution = resolveComposerText(
        params.composerText,
        params.resources,
        params.enabledSkills,
        params.enabledPrompts,
      );
      if (resolution.error) {
        return { warning: resolution.error };
      }
      const nextItem = {
        text: resolution.applied ? resolution.resolvedText : params.composerText,
        mode: params.mode,
      };
      return {
        queue: [...context.queue, nextItem],
        warning: null,
        pendingReset: true,
        cancelRequested: params.mode === "steer" ? true : context.cancelRequested,
      };
    }),
    requestSend: assign(({ event }) => {
      const params = event as Extract<QueueEvent, { type: "SEND.REQUEST" }>;
      if (!params.composerText && params.attachmentCount === 0) {
        return { warning: null };
      }
      const resolution = resolveComposerText(
        params.composerText,
        params.resources,
        params.enabledSkills,
        params.enabledPrompts,
      );
      if (resolution.error) {
        return { warning: resolution.error };
      }
      const pending = {
        text: resolution.applied ? resolution.resolvedText : params.composerText,
        mode: "follow-up" as const,
      };
      return {
        pendingSend: pending,
        warning: null,
      };
    }),
    handleRunChange: assign(({ context, event }) => {
      const params = event as Extract<QueueEvent, { type: "ASSISTANT.RUNNING.CHANGED" }>;
      if (context.wasRunning && !params.isRunning && context.queue.length > 0) {
        const [next, ...rest] = context.queue;
        return {
          queue: rest,
          pendingSend: next,
          wasRunning: params.isRunning,
        };
      }
      return { wasRunning: params.isRunning };
    }),
    clearPendingSend: assign({ pendingSend: null }),
    clearPendingReset: assign({ pendingReset: false }),
    clearCancelRequested: assign({ cancelRequested: false }),
  },
}).createMachine({
  id: "composerQueue",
  initial: "idle",
  context: ({ input }) => ({
    queue: input?.initialQueue ?? [],
    warning: null,
    pendingSend: null,
    pendingReset: false,
    cancelRequested: false,
    wasRunning: false,
  }),
  states: {
    idle: {},
  },
  on: {
    "QUEUE.REQUEST": { actions: "enqueueMessage" },
    "SEND.REQUEST": { actions: "requestSend" },
    "ASSISTANT.RUNNING.CHANGED": { actions: "handleRunChange" },
    "SEND.DISPATCHED": { actions: "clearPendingSend" },
    "RESET.ACK": { actions: "clearPendingReset" },
    "CANCEL.ACK": { actions: "clearCancelRequested" },
  },
});

export type { QueueContext, QueueEvent, QueueInput, QueueItem, QueueMode };
