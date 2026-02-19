import { assign, fromPromise, setup } from "xstate";

import type {
  ApiClient,
  PhoenixConfig,
  ProfilesResponse,
} from "@agentic-ai-playground/api-client";

type AppDataContext = {
  apiClient: ApiClient;
  profiles: ProfilesResponse | null;
  runMode: string;
  phoenixConfig: PhoenixConfig | null;
  errors: {
    profiles: string | null;
    phoenix: string | null;
  };
};

type AppDataInput = {
  apiClient: ApiClient;
};

type AppDataEvent =
  | { type: "RUNMODE.SET"; value: string }
  | { type: "PROFILES.RETRY" }
  | { type: "PHOENIX.RETRY" };

const resolveDefaultRunMode = (profiles: ProfilesResponse): string => {
  return profiles.defaultRunMode ?? profiles.runModes[0] ?? profiles.profiles[0]?.id ?? "";
};

const resolveErrorMessage = (error: unknown, fallback: string): string => {
  return error instanceof Error ? error.message : fallback;
};

export const appDataMachine = setup({
  types: {
    context: {} as AppDataContext,
    input: {} as AppDataInput,
    events: {} as AppDataEvent,
  },
  actors: {
    fetchProfiles: fromPromise(async ({ input }: { input: AppDataInput }) => {
      return input.apiClient.listProfiles();
    }),
    fetchPhoenix: fromPromise(async ({ input }: { input: AppDataInput }) => {
      return input.apiClient.getPhoenixConfig();
    }),
  },
  actions: {
    assignProfiles: assign(({ context, event }) => {
      if (!("output" in event)) {
        return {};
      }
      const profiles = (event as { output: ProfilesResponse }).output;
      return {
        profiles,
        runMode: context.runMode || resolveDefaultRunMode(profiles),
        errors: { ...context.errors, profiles: null },
      };
    }),
    assignProfilesError: assign(({ context, event }) => {
      if (!("error" in event)) {
        return {};
      }
      return {
        profiles: { profiles: [], runModes: [], defaultRunMode: null },
        errors: {
          ...context.errors,
          profiles: resolveErrorMessage(
            (event as { error: unknown }).error,
            "Failed to load profiles",
          ),
        },
      };
    }),
    assignPhoenix: assign(({ context, event }) => {
      if (!("output" in event)) {
        return {};
      }
      return {
        phoenixConfig: (event as { output: PhoenixConfig }).output,
        errors: { ...context.errors, phoenix: null },
      };
    }),
    assignPhoenixError: assign(({ context }) => {
      return {
        phoenixConfig: null,
        errors: { ...context.errors, phoenix: null },
      };
    }),
    assignRunMode: assign(({ event }) => {
      return {
        runMode: (event as { value: string }).value,
      };
    }),
  },
}).createMachine({
  id: "appData",
  type: "parallel",
  context: ({ input }) => ({
    apiClient: input.apiClient,
    profiles: null,
    runMode: "",
    phoenixConfig: null,
    errors: {
      profiles: null,
      phoenix: null,
    },
  }),
  on: {
    "RUNMODE.SET": { actions: "assignRunMode" },
  },
  states: {
    profiles: {
      initial: "loading",
      states: {
        loading: {
          invoke: {
            src: "fetchProfiles",
            input: ({ context }) => ({ apiClient: context.apiClient }),
            onDone: { target: "ready", actions: "assignProfiles" },
            onError: { target: "error", actions: "assignProfilesError" },
          },
        },
        ready: {
          on: { "PROFILES.RETRY": { target: "loading" } },
        },
        error: {
          on: { "PROFILES.RETRY": { target: "loading" } },
        },
      },
    },
    phoenix: {
      initial: "loading",
      states: {
        loading: {
          invoke: {
            src: "fetchPhoenix",
            input: ({ context }) => ({ apiClient: context.apiClient }),
            onDone: { target: "ready", actions: "assignPhoenix" },
            onError: { target: "error", actions: "assignPhoenixError" },
          },
        },
        ready: {
          on: { "PHOENIX.RETRY": { target: "loading" } },
        },
        error: {
          on: { "PHOENIX.RETRY": { target: "loading" } },
        },
      },
    },
  },
});

export type { AppDataContext, AppDataEvent, AppDataInput };
