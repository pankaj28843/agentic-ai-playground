import { assign, fromPromise, setup } from "xstate";

import type { ApiClient, SessionEntryView, SessionTreeResponse } from "@agentic-ai-playground/api-client";

type SessionTreeContext = {
  apiClient: ApiClient;
  threadId: string | null;
  tree: SessionTreeResponse | null;
  entriesById: Record<string, SessionEntryView>;
  activeEntryId: string | null;
  labelDraft: string;
  isLoading: boolean;
  error: string | null;
};

type SessionTreeInput = {
  apiClient: ApiClient;
};

type SessionTreeEvent =
  | { type: "THREAD.SET"; threadId: string | null }
  | { type: "TREE.REFRESH" }
  | { type: "ENTRY.SET_ACTIVE"; entryId: string | null }
  | { type: "ENTRY.LABEL.DRAFT.SET"; value: string }
  | { type: "ENTRY.LABEL"; entryId: string; label: string | null };

const buildEntriesById = (tree: SessionTreeResponse | null): Record<string, SessionEntryView> => {
  if (!tree) {
    return {};
  }
  return tree.entries.reduce<Record<string, SessionEntryView>>((acc, entry) => {
    acc[entry.id] = entry;
    return acc;
  }, {});
};

const resolveLabelDraft = (
  entriesById: Record<string, SessionEntryView>,
  activeEntryId: string | null,
): string => {
  if (!activeEntryId) {
    return "";
  }
  return entriesById[activeEntryId]?.label ?? "";
};

export const sessionTreeMachine = setup({
  types: {
    context: {} as SessionTreeContext,
    input: {} as SessionTreeInput,
    events: {} as SessionTreeEvent,
  },
  actors: {
    fetchTree: fromPromise(
      async ({ input }: { input: { apiClient: ApiClient; threadId: string } }) => {
        return input.apiClient.getSessionTree(input.threadId);
      },
    ),
    labelEntry: fromPromise(
      async ({
        input,
      }: {
        input: { apiClient: ApiClient; threadId: string; entryId: string; label: string | null };
      }) => {
        await input.apiClient.labelSessionEntry(input.threadId, input.entryId, input.label);
        return input.threadId;
      },
    ),
  },
  actions: {
    assignThread: assign(({ event }) => ({
      threadId: (event as { threadId: string | null }).threadId,
      activeEntryId: null,
      labelDraft: "",
    })),
    clearTree: assign({
      tree: null,
      entriesById: {},
      labelDraft: "",
      error: null,
      isLoading: false,
    }),
    assignTree: assign(({ context, event }) => {
      if (!("output" in event)) {
        return {};
      }
      const tree = (event as { output: SessionTreeResponse }).output;
      const entriesById = buildEntriesById(tree);
      const activeEntryId = context.activeEntryId ?? tree.leafId ?? null;
      return {
        tree,
        entriesById,
        labelDraft: resolveLabelDraft(entriesById, activeEntryId),
        error: null,
        isLoading: false,
      };
    }),
    assignError: assign(({ event }) => {
      if (!("error" in event)) {
        return {};
      }
      const error = (event as { error: unknown }).error;
      return {
        tree: null,
        entriesById: {},
        error: error instanceof Error ? error.message : "Failed to load session tree",
        isLoading: false,
      };
    }),
    assignActiveEntry: assign(({ context, event }) => ({
      activeEntryId: (event as { entryId: string | null }).entryId,
      labelDraft: resolveLabelDraft(
        context.entriesById,
        (event as { entryId: string | null }).entryId,
      ),
    })),
    assignLabelDraft: assign(({ event }) => ({
      labelDraft: (event as { value: string }).value,
    })),
  },
}).createMachine({
  id: "sessionTree",
  initial: "idle",
  context: ({ input }) => ({
    apiClient: input.apiClient,
    threadId: null,
    tree: null,
    entriesById: {},
    activeEntryId: null,
    labelDraft: "",
    isLoading: false,
    error: null,
  }),
  states: {
    idle: {
      on: {
        "THREAD.SET": [
          {
            guard: ({ event }) => !(event as { threadId: string | null }).threadId,
            actions: ["assignThread", "clearTree"],
          },
          { target: "loading", actions: "assignThread" },
        ],
      },
    },
    loading: {
      entry: assign({ isLoading: true }),
      invoke: {
        src: "fetchTree",
        input: ({ context }) => ({
          apiClient: context.apiClient,
          threadId: context.threadId ?? "",
        }),
        onDone: { target: "ready", actions: "assignTree" },
        onError: { target: "error", actions: "assignError" },
      },
      on: {
        "THREAD.SET": { target: "idle", actions: "assignThread" },
      },
    },
    ready: {
      on: {
        "TREE.REFRESH": { target: "loading" },
        "ENTRY.SET_ACTIVE": { actions: "assignActiveEntry" },
        "ENTRY.LABEL.DRAFT.SET": { actions: "assignLabelDraft" },
        "ENTRY.LABEL": { target: "labeling" },
        "THREAD.SET": { target: "idle", actions: "assignThread" },
      },
    },
    labeling: {
      entry: assign({ isLoading: true }),
      invoke: {
        src: "labelEntry",
        input: ({ context, event }) => ({
          apiClient: context.apiClient,
          threadId: context.threadId ?? "",
          entryId: (event as { entryId: string }).entryId,
          label: (event as { label: string | null }).label,
        }),
        onDone: { target: "loading" },
        onError: { target: "error", actions: "assignError" },
      },
    },
    error: {
      on: {
        "TREE.REFRESH": { target: "loading" },
        "THREAD.SET": { target: "idle", actions: "assignThread" },
        "ENTRY.LABEL.DRAFT.SET": { actions: "assignLabelDraft" },
      },
    },
  },
});

export type { SessionTreeContext, SessionTreeEvent, SessionTreeInput };
