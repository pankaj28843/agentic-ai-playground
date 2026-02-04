import { useCallback } from "react";

import { useOverridesActor, useOverridesSelector } from "./overridesContext";

export const useOverrides = () => {
  const actorRef = useOverridesActor();
  const modelOverride = useOverridesSelector((state) => state.context.modelOverride);
  const toolGroupsOverride = useOverridesSelector((state) => state.context.toolGroupsOverride);
  const isLoading = useOverridesSelector((state) => state.context.isLoading);

  const setModelOverride = useCallback(
    (value: string | null) => {
      actorRef.send({ type: "OVERRIDE.MODEL.SET", value });
    },
    [actorRef],
  );

  const setToolGroupsOverride = useCallback(
    (value: string[] | null) => {
      actorRef.send({ type: "OVERRIDE.TOOLGROUPS.SET", value });
    },
    [actorRef],
  );

  return {
    modelOverride,
    toolGroupsOverride,
    setModelOverride,
    setToolGroupsOverride,
    isLoading,
  };
};
