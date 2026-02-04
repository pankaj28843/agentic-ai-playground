import { useOverridesActor, useOverridesSelector } from "./overridesContext";

export const useOverrides = () => {
  const actorRef = useOverridesActor();
  const modelOverride = useOverridesSelector((state) => state.context.modelOverride);
  const toolGroupsOverride = useOverridesSelector((state) => state.context.toolGroupsOverride);
  const isLoading = useOverridesSelector((state) => state.context.isLoading);

  const setModelOverride = (value: string | null) => {
    actorRef.send({ type: "OVERRIDE.MODEL.SET", value });
  };

  const setToolGroupsOverride = (value: string[] | null) => {
    actorRef.send({ type: "OVERRIDE.TOOLGROUPS.SET", value });
  };

  return {
    modelOverride,
    toolGroupsOverride,
    setModelOverride,
    setToolGroupsOverride,
    isLoading,
  };
};
