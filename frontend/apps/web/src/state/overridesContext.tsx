import type { ReactNode } from "react";
import { useEffect } from "react";

/* eslint-disable react-refresh/only-export-components */
import { createActorContext } from "@xstate/react";
import type { SnapshotFrom } from "xstate";

import type { ApiClient } from "@agentic-ai-playground/api-client";
import { overridesMachine, readStoredOverrides } from "./overridesMachine";

export type OverridesSnapshot = SnapshotFrom<typeof overridesMachine>;

const OverridesActorContext = createActorContext(overridesMachine);

export const OverridesProvider = ({
  apiClient,
  threadId,
  children,
}: {
  apiClient: ApiClient;
  threadId: string | null;
  children: ReactNode;
}) => {
  const storedOverrides = readStoredOverrides();

  return (
    <OverridesActorContext.Provider
      logic={overridesMachine}
      options={{ input: { apiClient, storedOverrides } }}
    >
      <OverridesThreadSync threadId={threadId} />
      {children}
    </OverridesActorContext.Provider>
  );
};

const OverridesThreadSync = ({ threadId }: { threadId: string | null }) => {
  const actorRef = OverridesActorContext.useActorRef();

  useEffect(() => {
    actorRef.send({ type: "THREAD.SET", threadId });
  }, [actorRef, threadId]);

  return null;
};

export const useOverridesActor = () => OverridesActorContext.useActorRef();

export const useOverridesSelector = <T,>(
  selector: (snapshot: OverridesSnapshot) => T,
): T => {
  return OverridesActorContext.useSelector(selector);
};
