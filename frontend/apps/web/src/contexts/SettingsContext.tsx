import type { ReactNode } from "react";

import type { InferenceProfileSummary, ProfileDefaults, ToolGroupSummary } from "@agentic-ai-playground/api-client";

import { useAppDataSelector } from "../state/appDataContext";
import { useOverrides } from "../state/useOverrides";

export type SettingsState = {
  models: string[];
  defaultModel: string | null;
  toolGroups: ToolGroupSummary[];
  profileDefaults: ProfileDefaults[];
  inferenceProfiles: InferenceProfileSummary[];
  warnings: string[];
  modelOverride: string | null;
  toolGroupsOverride: string[] | null;
  setModelOverride: (value: string | null) => void;
  setToolGroupsOverride: (value: string[] | null) => void;
  isLoading: boolean;
  error: string | null;
};

export const useSettings = (): SettingsState => {
  const settings = useAppDataSelector((state) => state.context.settings);
  const error = useAppDataSelector((state) => state.context.errors.settings);
  const isLoading = useAppDataSelector((state) => state.matches({ settings: "loading" }));
  const { modelOverride, toolGroupsOverride, setModelOverride, setToolGroupsOverride } =
    useOverrides();

  return {
    models: settings?.models ?? [],
    defaultModel: settings?.defaultModel ?? null,
    toolGroups: settings?.toolGroups ?? [],
    profileDefaults: settings?.profileDefaults ?? [],
    inferenceProfiles: settings?.inferenceProfiles ?? [],
    warnings: settings?.warnings ?? [],
    modelOverride,
    toolGroupsOverride,
    setModelOverride,
    setToolGroupsOverride,
    isLoading,
    error,
  };
};

export const SettingsProvider = ({ children }: { children: ReactNode }) => children;
