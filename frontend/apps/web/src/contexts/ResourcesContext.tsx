import type { ReactNode } from "react";

import type { ResourcesResponse } from "@agentic-ai-playground/api-client";

import { useAppDataActor, useAppDataSelector } from "../state/appDataContext";

export type ResourcesState = {
  resources: ResourcesResponse | null;
  isLoading: boolean;
  error: string | null;
  enabledSkills: string[];
  enabledPrompts: string[];
  setEnabledSkills: (names: string[]) => void;
  setEnabledPrompts: (names: string[]) => void;
};

export const useResources = (): ResourcesState => {
  const actorRef = useAppDataActor();
  const resources = useAppDataSelector((state) => state.context.resources);
  const enabledSkills = useAppDataSelector((state) => state.context.enabledSkills);
  const enabledPrompts = useAppDataSelector((state) => state.context.enabledPrompts);
  const error = useAppDataSelector((state) => state.context.errors.resources);
  const isLoading = useAppDataSelector((state) => state.matches({ resources: "loading" }));

  return {
    resources,
    enabledSkills,
    enabledPrompts,
    isLoading,
    error,
    setEnabledSkills: (names) => actorRef.send({ type: "RESOURCES.SKILLS.SET", values: names }),
    setEnabledPrompts: (names) => actorRef.send({ type: "RESOURCES.PROMPTS.SET", values: names }),
  };
};

export const ResourcesProvider = ({ children }: { children: ReactNode }) => children;
