import type { ReactNode } from "react";
import { useEffect } from "react";

import { useThreadList } from "@assistant-ui/react";
import { ApiClient } from "@agentic-ai-playground/api-client";
import { setActiveSessionBranch } from "@agentic-ai-playground/assistant-runtime";
/* eslint-disable react-refresh/only-export-components */
import { createActorContext } from "@xstate/react";

import type { SessionEntryView, SessionTreeResponse } from "@agentic-ai-playground/api-client";
import { sessionTreeMachine } from "../state/sessionTreeMachine";

export type SessionTreeState = {
  threadId: string | null;
  tree: SessionTreeResponse | null;
  entriesById: Record<string, SessionEntryView>;
  activeEntryId: string | null;
  labelDraft: string;
  setActiveEntryId: (entryId: string | null) => void;
  setLabelDraft: (value: string) => void;
  refresh: () => Promise<void>;
  labelEntry: (entryId: string, label: string | null) => Promise<void>;
  isLoading: boolean;
  error: string | null;
};

const SessionTreeActorContext = createActorContext(sessionTreeMachine);
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
const sessionTreeApiClient = new ApiClient(baseUrl);

export const SessionTreeProvider = ({ children }: { children: ReactNode }) => {
  return (
    <SessionTreeActorContext.Provider
      logic={sessionTreeMachine}
      options={{ input: { apiClient: sessionTreeApiClient } }}
    >
      <SessionTreeBridge />
      {children}
    </SessionTreeActorContext.Provider>
  );
};

const SessionTreeBridge = () => {
  const actorRef = SessionTreeActorContext.useActorRef();
  const threadId = useThreadId();
  const activeEntryId = SessionTreeActorContext.useSelector(
    (state) => state.context.activeEntryId,
  );

  useEffect(() => {
    actorRef.send({ type: "THREAD.SET", threadId });
  }, [actorRef, threadId]);

  useEffect(() => {
    if (!threadId) {
      setActiveSessionBranch(null);
      return;
    }
    if (activeEntryId) {
      setActiveSessionBranch({ threadId, entryId: activeEntryId });
    } else {
      setActiveSessionBranch(null);
    }
  }, [activeEntryId, threadId]);

  return null;
};

const useThreadId = () => {
  const mainThreadId = useThreadList((state) => state.mainThreadId);
  const threadItems = useThreadList((state) => state.threadItems);

  if (!mainThreadId) {
    return null;
  }
  const remoteId = threadItems[mainThreadId]?.remoteId ?? mainThreadId;
  if (!remoteId || remoteId.startsWith("__")) {
    return null;
  }
  return remoteId;
};

export const useSessionTree = () => {
  const actorRef = SessionTreeActorContext.useActorRef();
  const threadId = SessionTreeActorContext.useSelector((state) => state.context.threadId);
  const tree = SessionTreeActorContext.useSelector((state) => state.context.tree);
  const entriesById = SessionTreeActorContext.useSelector((state) => state.context.entriesById);
  const activeEntryId = SessionTreeActorContext.useSelector(
    (state) => state.context.activeEntryId,
  );
  const labelDraft = SessionTreeActorContext.useSelector((state) => state.context.labelDraft);
  const isLoading = SessionTreeActorContext.useSelector((state) => state.context.isLoading);
  const error = SessionTreeActorContext.useSelector((state) => state.context.error);

  const setActiveEntryId = (entryId: string | null) => {
    actorRef.send({ type: "ENTRY.SET_ACTIVE", entryId });
  };

  const setLabelDraft = (value: string) => {
    actorRef.send({ type: "ENTRY.LABEL.DRAFT.SET", value });
  };

  const refresh = async () => {
    actorRef.send({ type: "TREE.REFRESH" });
  };

  const labelEntry = async (entryId: string, label: string | null) => {
    actorRef.send({ type: "ENTRY.LABEL", entryId, label });
  };

  return {
    threadId,
    tree,
    entriesById,
    activeEntryId,
    labelDraft,
    setActiveEntryId,
    setLabelDraft,
    refresh,
    labelEntry,
    isLoading,
    error,
  };
};
