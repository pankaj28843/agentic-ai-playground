import type { ReactNode } from "react";
import { createContext, useContext } from "react";

import type { ResourcesResponse } from "@agentic-ai-playground/api-client";

export type ResourcesState = {
  resources: ResourcesResponse | null;
  isLoading: boolean;
  error: string | null;
  enabledSkills: string[];
  enabledPrompts: string[];
  setEnabledSkills: (names: string[]) => void;
  setEnabledPrompts: (names: string[]) => void;
};

const ResourcesContext = createContext<ResourcesState>({
  resources: null,
  isLoading: true,
  error: null,
  enabledSkills: [],
  enabledPrompts: [],
  setEnabledSkills: () => undefined,
  setEnabledPrompts: () => undefined,
});

export const ResourcesProvider = ({
  value,
  children,
}: {
  value: ResourcesState;
  children: ReactNode;
}) => {
  return <ResourcesContext.Provider value={value}>{children}</ResourcesContext.Provider>;
};

export const useResources = () => useContext(ResourcesContext);
