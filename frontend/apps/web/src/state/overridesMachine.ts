import { assign, fromPromise, setup } from "xstate";

import type { ApiClient, ThreadDetail } from "@agentic-ai-playground/api-client";

type OverridesContext = {
  apiClient: ApiClient;
  threadId: string | null;
  modelOverride: string | null;
  toolGroupsOverride: string[] | null;
  isLoading: boolean;
};

type OverridesInput = {
  apiClient: ApiClient;
  storedOverrides: StoredOverrides;
};

type StoredOverrides = {
  modelOverride: string | null;
  toolGroupsOverride: string[] | null;
};

type OverridesEvent =
  | { type: "THREAD.SET"; threadId: string | null }
  | { type: "OVERRIDE.MODEL.SET"; value: string | null }
  | { type: "OVERRIDE.TOOLGROUPS.SET"; value: string[] | null };

const STORAGE_KEY = "playground-run-overrides-v1";

const readStoredOverrides = (): StoredOverrides => {
  if (typeof window === "undefined") {
    return { modelOverride: null, toolGroupsOverride: null };
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { modelOverride: null, toolGroupsOverride: null };
    }
    const parsed = JSON.parse(raw) as StoredOverrides;
    return {
      modelOverride: typeof parsed.modelOverride === "string" ? parsed.modelOverride : null,
      toolGroupsOverride: Array.isArray(parsed.toolGroupsOverride)
        ? parsed.toolGroupsOverride.filter((value) => typeof value === "string")
        : null,
    };
  } catch {
    return { modelOverride: null, toolGroupsOverride: null };
  }
};

const writeStoredOverrides = (overrides: StoredOverrides): void => {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
  } catch {
    // Ignore storage errors
  }
};

const resolveThreadOverrides = (thread: ThreadDetail | null): StoredOverrides => {
  if (!thread) {
    return { modelOverride: null, toolGroupsOverride: null };
  }
  return {
    modelOverride: thread.modelOverride ?? null,
    toolGroupsOverride: thread.toolGroupsOverride ?? null,
  };
};

export const overridesMachine = setup({
  types: {
    context: {} as OverridesContext,
    input: {} as OverridesInput,
    events: {} as OverridesEvent,
  },
  actors: {
    fetchThread: fromPromise(async ({ input }: { input: { apiClient: ApiClient; threadId: string } }) => {
      const thread = await input.apiClient.getThread(input.threadId);
      return { thread, fallback: readStoredOverrides() };
    }),
  },
  actions: {
    assignThread: assign(({ event }) => {
      return {
        threadId: (event as { threadId: string | null }).threadId,
        isLoading: false,
      };
    }),
    assignOverridesFromThread: assign(({ event }) => {
      if (!("output" in event)) {
        return {};
      }
      const output = (event as { output: { thread: ThreadDetail; fallback: StoredOverrides } }).output;
      const overrides = resolveThreadOverrides(output.thread);
      const merged = {
        modelOverride: overrides.modelOverride ?? output.fallback.modelOverride,
        toolGroupsOverride: overrides.toolGroupsOverride ?? output.fallback.toolGroupsOverride,
      };
      return {
        modelOverride: merged.modelOverride,
        toolGroupsOverride: merged.toolGroupsOverride,
        isLoading: false,
      };
    }),
    assignModelOverride: assign(({ context, event }) => {
      const value = (event as { value: string | null }).value;
      const overrides = {
        modelOverride: value,
        toolGroupsOverride: context.toolGroupsOverride,
      };
      writeStoredOverrides(overrides);
      return {
        modelOverride: overrides.modelOverride,
        toolGroupsOverride: overrides.toolGroupsOverride,
        isLoading: false,
      };
    }),
    assignToolOverrides: assign(({ context, event }) => {
      const value = (event as { value: string[] | null }).value;
      const overrides = {
        modelOverride: context.modelOverride,
        toolGroupsOverride: value,
      };
      writeStoredOverrides(overrides);
      return {
        modelOverride: overrides.modelOverride,
        toolGroupsOverride: overrides.toolGroupsOverride,
        isLoading: false,
      };
    }),
  },
}).createMachine({
  id: "overrides",
  initial: "idle",
  context: ({ input }) => ({
    apiClient: input.apiClient,
    threadId: null,
    modelOverride: input.storedOverrides.modelOverride,
    toolGroupsOverride: input.storedOverrides.toolGroupsOverride,
    isLoading: false,
  }),
  states: {
    idle: {
      on: {
        "THREAD.SET": [
          {
            guard: ({ event }) => !(event as { threadId: string | null }).threadId,
            actions: [
              "assignThread",
              ({ self }) => {
                self.send({
                  type: "OVERRIDE.MODEL.SET",
                  value: readStoredOverrides().modelOverride,
                });
                self.send({
                  type: "OVERRIDE.TOOLGROUPS.SET",
                  value: readStoredOverrides().toolGroupsOverride,
                });
              },
            ],
          },
          {
            target: "loading",
            actions: "assignThread",
          },
        ],
        "OVERRIDE.MODEL.SET": { actions: "assignModelOverride" },
        "OVERRIDE.TOOLGROUPS.SET": { actions: "assignToolOverrides" },
      },
    },
    loading: {
      entry: assign({ isLoading: true }),
      invoke: {
        src: "fetchThread",
        input: ({ context }) => ({
          apiClient: context.apiClient,
          threadId: context.threadId ?? "",
        }),
        onDone: { target: "idle", actions: "assignOverridesFromThread" },
        onError: {
          target: "idle",
          actions: ({ self }) => {
            const fallback = readStoredOverrides();
            self.send({
              type: "OVERRIDE.MODEL.SET",
              value: fallback.modelOverride,
            });
            self.send({
              type: "OVERRIDE.TOOLGROUPS.SET",
              value: fallback.toolGroupsOverride,
            });
          },
        },
      },
      on: {
        "OVERRIDE.MODEL.SET": { target: "idle", actions: "assignModelOverride" },
        "OVERRIDE.TOOLGROUPS.SET": { target: "idle", actions: "assignToolOverrides" },
        "THREAD.SET": { target: "idle", actions: "assignThread" },
      },
    },
  },
});

export { readStoredOverrides, writeStoredOverrides };
export type { OverridesContext, OverridesEvent, OverridesInput, StoredOverrides };
