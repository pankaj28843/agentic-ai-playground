import type { ReactNode } from "react";
import { createContext, useContext } from "react";

import type { ProfileDefaults, ToolGroupSummary } from "@agentic-ai-playground/api-client";

export type SettingsState = {
  models: string[];
  defaultModel: string | null;
  toolGroups: ToolGroupSummary[];
  profileDefaults: ProfileDefaults[];
  modelOverride: string | null;
  toolGroupsOverride: string[] | null;
  setModelOverride: (value: string | null) => void;
  setToolGroupsOverride: (value: string[] | null) => void;
  isLoading: boolean;
  error: string | null;
};

const SettingsContext = createContext<SettingsState>({
  models: [],
  defaultModel: null,
  toolGroups: [],
  profileDefaults: [],
  modelOverride: null,
  toolGroupsOverride: null,
  setModelOverride: () => undefined,
  setToolGroupsOverride: () => undefined,
  isLoading: false,
  error: null,
});

export const SettingsProvider = ({
  value,
  children,
}: {
  value: SettingsState;
  children: ReactNode;
}) => {
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
};

export const useSettings = () => useContext(SettingsContext);
