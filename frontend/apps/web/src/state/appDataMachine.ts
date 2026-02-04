import { assign, fromPromise, setup } from "xstate";

import type {
  ApiClient,
  PhoenixConfig,
  ProfilesResponse,
  ResourcesResponse,
  SettingsResponse,
} from "@agentic-ai-playground/api-client";

type AppDataContext = {
  apiClient: ApiClient;
  profiles: ProfilesResponse | null;
  runMode: string;
  settings: SettingsResponse | null;
  resources: ResourcesResponse | null;
  phoenixConfig: PhoenixConfig | null;
  enabledSkills: string[];
  enabledPrompts: string[];
  errors: {
    profiles: string | null;
    settings: string | null;
    resources: string | null;
    phoenix: string | null;
  };
};

type AppDataInput = {
  apiClient: ApiClient;
};

type AppDataEvent =
  | { type: "RUNMODE.SET"; value: string }
  | { type: "RESOURCES.SKILLS.SET"; values: string[] }
  | { type: "RESOURCES.PROMPTS.SET"; values: string[] }
  | { type: "PROFILES.RETRY" }
  | { type: "SETTINGS.RETRY" }
  | { type: "RESOURCES.RETRY" }
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
    fetchSettings: fromPromise(async ({ input }: { input: AppDataInput }) => {
      return input.apiClient.getSettings();
    }),
    fetchResources: fromPromise(async ({ input }: { input: AppDataInput }) => {
      return input.apiClient.listResources();
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
    assignSettings: assign(({ context, event }) => {
      if (!("output" in event)) {
        return {};
      }
      return {
        settings: (event as { output: SettingsResponse }).output,
        errors: { ...context.errors, settings: null },
      };
    }),
    assignSettingsError: assign(({ context, event }) => {
      if (!("error" in event)) {
        return {};
      }
      return {
        settings: null,
        errors: {
          ...context.errors,
          settings: resolveErrorMessage(
            (event as { error: unknown }).error,
            "Failed to load settings",
          ),
        },
      };
    }),
    assignResources: assign(({ context, event }) => {
      if (!("output" in event)) {
        return {};
      }
      const resources = (event as { output: ResourcesResponse }).output;
      const shouldInitEnabled =
        context.enabledSkills.length === 0 && context.enabledPrompts.length === 0;
      return {
        resources,
        enabledSkills: shouldInitEnabled
          ? resources.skills.map((skill) => skill.name)
          : context.enabledSkills,
        enabledPrompts: shouldInitEnabled
          ? resources.prompts.map((prompt) => prompt.name)
          : context.enabledPrompts,
        errors: { ...context.errors, resources: null },
      };
    }),
    assignResourcesError: assign(({ context, event }) => {
      if (!("error" in event)) {
        return {};
      }
      return {
        resources: null,
        errors: {
          ...context.errors,
          resources: resolveErrorMessage(
            (event as { error: unknown }).error,
            "Failed to load resources",
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
    assignEnabledSkills: assign(({ event }) => {
      return {
        enabledSkills: (event as { values: string[] }).values,
      };
    }),
    assignEnabledPrompts: assign(({ event }) => {
      return {
        enabledPrompts: (event as { values: string[] }).values,
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
    settings: null,
    resources: null,
    phoenixConfig: null,
    enabledSkills: [],
    enabledPrompts: [],
    errors: {
      profiles: null,
      settings: null,
      resources: null,
      phoenix: null,
    },
  }),
  on: {
    "RUNMODE.SET": { actions: "assignRunMode" },
    "RESOURCES.SKILLS.SET": { actions: "assignEnabledSkills" },
    "RESOURCES.PROMPTS.SET": { actions: "assignEnabledPrompts" },
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
    settings: {
      initial: "loading",
      states: {
        loading: {
          invoke: {
            src: "fetchSettings",
            input: ({ context }) => ({ apiClient: context.apiClient }),
            onDone: { target: "ready", actions: "assignSettings" },
            onError: { target: "error", actions: "assignSettingsError" },
          },
        },
        ready: {
          on: { "SETTINGS.RETRY": { target: "loading" } },
        },
        error: {
          on: { "SETTINGS.RETRY": { target: "loading" } },
        },
      },
    },
    resources: {
      initial: "loading",
      states: {
        loading: {
          invoke: {
            src: "fetchResources",
            input: ({ context }) => ({ apiClient: context.apiClient }),
            onDone: { target: "ready", actions: "assignResources" },
            onError: { target: "error", actions: "assignResourcesError" },
          },
        },
        ready: {
          on: { "RESOURCES.RETRY": { target: "loading" } },
        },
        error: {
          on: { "RESOURCES.RETRY": { target: "loading" } },
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
