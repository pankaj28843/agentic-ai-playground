import type { ReactNode } from "react";
import { useCallback } from "react";

/* eslint-disable react-refresh/only-export-components */
import { createActorContext } from "@xstate/react";
import type { SnapshotFrom } from "xstate";

import { appShellMachine } from "./appShellMachine";

type AppShellSnapshot = SnapshotFrom<typeof appShellMachine>;

const AppShellActorContext = createActorContext(appShellMachine);

export const AppShellProvider = ({ children }: { children: ReactNode }) => {
  return (
    <AppShellActorContext.Provider logic={appShellMachine}>
      {children}
    </AppShellActorContext.Provider>
  );
};

export const useAppShellActor = () => AppShellActorContext.useActorRef();

export const useAppShellSelector = <T,>(selector: (snapshot: AppShellSnapshot) => T): T => {
  return AppShellActorContext.useSelector(selector);
};

export const useAppShell = () => {
  const actorRef = useAppShellActor();
  const menuOpen = useAppShellSelector((state) => state.context.menuOpen);
  const shouldCloseTrace = useAppShellSelector((state) => state.context.shouldCloseTrace);

  const toggleMenu = useCallback(() => {
    actorRef.send({ type: "MENU.TOGGLE" });
  }, [actorRef]);

  const openMenu = useCallback(() => {
    actorRef.send({ type: "MENU.OPEN" });
  }, [actorRef]);

  const closeMenu = useCallback(() => {
    actorRef.send({ type: "MENU.CLOSE" });
  }, [actorRef]);

  const setConversationId = useCallback(
    (value: string | null) => {
      actorRef.send({ type: "ROUTE.CONVERSATION.SET", value });
    },
    [actorRef],
  );

  const acknowledgeTraceClosed = useCallback(() => {
    actorRef.send({ type: "TRACE.CLOSE.ACK" });
  }, [actorRef]);

  return {
    menuOpen,
    shouldCloseTrace,
    toggleMenu,
    openMenu,
    closeMenu,
    setConversationId,
    acknowledgeTraceClosed,
  };
};

export type { AppShellSnapshot };
