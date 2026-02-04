import type { ReactNode } from "react";

/* eslint-disable react-refresh/only-export-components */
import { createActorContext } from "@xstate/react";
import type { SnapshotFrom } from "xstate";

import type { ApiClient } from "@agentic-ai-playground/api-client";
import { appDataMachine } from "./appDataMachine";

export type AppDataSnapshot = SnapshotFrom<typeof appDataMachine>;

const AppDataActorContext = createActorContext(appDataMachine);

export const AppDataProvider = ({
  apiClient,
  children,
}: {
  apiClient: ApiClient;
  children: ReactNode;
}) => {
  return (
    <AppDataActorContext.Provider
      logic={appDataMachine}
      options={{ input: { apiClient } }}
    >
      {children}
    </AppDataActorContext.Provider>
  );
};

export const useAppDataActor = () => AppDataActorContext.useActorRef();

export const useAppDataSelector = <T,>(selector: (snapshot: AppDataSnapshot) => T): T => {
  return AppDataActorContext.useSelector(selector);
};
