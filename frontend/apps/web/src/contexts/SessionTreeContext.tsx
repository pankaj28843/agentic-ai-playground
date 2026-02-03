import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useThreadList } from "@assistant-ui/react";
import type { SessionEntryView, SessionTreeResponse } from "@agentic-ai-playground/api-client";
import { ApiClient } from "@agentic-ai-playground/api-client";
import { setActiveSessionBranch } from "@agentic-ai-playground/assistant-runtime";

export type SessionTreeState = {
  threadId: string | null;
  tree: SessionTreeResponse | null;
  entriesById: Record<string, SessionEntryView>;
  activeEntryId: string | null;
  setActiveEntryId: (entryId: string | null) => void;
  refresh: () => Promise<void>;
  labelEntry: (entryId: string, label: string | null) => Promise<void>;
  isLoading: boolean;
  error: string | null;
};

const SessionTreeContext = createContext<SessionTreeState>({
  threadId: null,
  tree: null,
  entriesById: {},
  activeEntryId: null,
  setActiveEntryId: () => undefined,
  refresh: async () => undefined,
  labelEntry: async () => undefined,
  isLoading: false,
  error: null,
});

export const SessionTreeProvider = ({ children }: { children: ReactNode }) => {
  const mainThreadId = useThreadList((state) => state.mainThreadId);
  const threadItems = useThreadList((state) => state.threadItems);
  const [tree, setTree] = useState<SessionTreeResponse | null>(null);
  const [activeEntryId, setActiveEntryId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const apiClient = useMemo(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    return new ApiClient(baseUrl);
  }, []);

  const threadId = useMemo(() => {
    if (!mainThreadId) {
      return null;
    }
    const remoteId = threadItems[mainThreadId]?.remoteId ?? mainThreadId;
    if (!remoteId || remoteId.startsWith("__")) {
      return null;
    }
    return remoteId;
  }, [mainThreadId, threadItems]);

  const entriesById = useMemo(() => {
    if (!tree) {
      return {};
    }
    return tree.entries.reduce<Record<string, SessionEntryView>>((acc, entry) => {
      acc[entry.id] = entry;
      return acc;
    }, {});
  }, [tree]);

  const fetchTree = useCallback(async () => {
    if (!threadId) {
      setTree(null);
      setError(null);
      return;
    }
    setIsLoading(true);
    try {
      const response = await apiClient.getSessionTree(threadId);
      setTree(response);
      setError(null);
    } catch (err) {
      setTree(null);
      setError(err instanceof Error ? err.message : "Failed to load session tree");
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, threadId]);

  const labelEntry = useCallback(
    async (entryId: string, label: string | null) => {
      if (!threadId) {
        return;
      }
      await apiClient.labelSessionEntry(threadId, entryId, label);
      await fetchTree();
    },
    [apiClient, fetchTree, threadId],
  );

  useEffect(() => {
    void fetchTree();
  }, [fetchTree]);

  useEffect(() => {
    if (!threadId) {
      setActiveEntryId(null);
      setActiveSessionBranch(null);
      return;
    }
    if (activeEntryId) {
      setActiveSessionBranch({ threadId, entryId: activeEntryId });
    } else {
      setActiveSessionBranch(null);
    }
  }, [activeEntryId, threadId]);

  useEffect(() => {
    setActiveEntryId(null);
    setActiveSessionBranch(null);
  }, [threadId]);

  const value = useMemo<SessionTreeState>(
    () => ({
      threadId,
      tree,
      entriesById,
      activeEntryId,
      setActiveEntryId,
      refresh: fetchTree,
      labelEntry,
      isLoading,
      error,
    }),
    [activeEntryId, entriesById, error, fetchTree, isLoading, labelEntry, threadId, tree],
  );

  return <SessionTreeContext.Provider value={value}>{children}</SessionTreeContext.Provider>;
};

export const useSessionTree = () => useContext(SessionTreeContext);
