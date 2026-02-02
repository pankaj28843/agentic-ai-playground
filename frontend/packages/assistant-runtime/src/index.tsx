import type { ReactNode } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  AssistantRuntimeProvider as RuntimeProvider,
  unstable_useRemoteThreadListRuntime as useRemoteThreadListRuntime,
  useAssistantRuntime,
  useLocalRuntime,
  useThreadList,
} from "@assistant-ui/react";

import { ApiClient } from "@agentic-ai-playground/api-client";
import { createChatAdapter, threadListAdapter } from "./adapters";

// Re-export converters for external use
export { toApiMessage, toThreadMessage, buildRepository } from "./converters";

const baseUrl =
  (import.meta as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ?? "";

const api = new ApiClient(baseUrl);

const useLocalRuntimeAdapter = (runMode?: string) =>
  useLocalRuntime(createChatAdapter(runMode));

const useRuntimeHook = (runMode?: string) => {
  return useLocalRuntimeAdapter(runMode);
};

export const AssistantRuntimeProvider = ({
  children,
  runMode,
}: {
  children: ReactNode;
  runMode?: string;
}) => {
  // eslint-disable-next-line react-hooks/rules-of-hooks -- runtimeHook is called by useRemoteThreadListRuntime as a hook factory
  const runtimeHook = useCallback(() => useRuntimeHook(runMode), [runMode]);
  const runtime = useRemoteThreadListRuntime({
    runtimeHook,
    adapter: threadListAdapter,
  });

  return <RuntimeProvider runtime={runtime}>{children}</RuntimeProvider>;
};

/**
 * Hook to synchronize the URL with the selected thread.
 *
 * On initial load: if URL has a thread ID, switch to that thread.
 * When user selects a thread: update the URL.
 *
 * @param urlThreadId - The thread ID from the URL (e.g., from useParams)
 * @param onThreadChange - Callback when the selected thread changes
 * @returns Object with loading and error states for the URL thread
 */
export const useThreadRouterSync = (
  urlThreadId: string | undefined,
  onThreadChange: (threadId: string | null) => void,
): { isLoadingThread: boolean; threadNotFound: boolean } => {
  const runtime = useAssistantRuntime();
  const mainThreadId = useThreadList((s) => s.mainThreadId);
  const isLoading = useThreadList((s) => s.isLoading);
  const threadIds = useThreadList((s) => s.threadIds);

  // Also track remoteId for the current thread to detect when it gets persisted
  const threadItems = useThreadList((s) => s.threadItems);
  const currentRemoteId = mainThreadId ? threadItems[mainThreadId]?.remoteId : undefined;

  // Track sync state to avoid infinite loops
  const syncState = useRef<{
    initialSyncDone: boolean;
    lastUrlThreadId: string | undefined;
    lastMainThreadId: string | undefined;
    lastRemoteId: string | undefined;
    threadNotFound: boolean;
    isSwitchingThread: boolean;
  }>({
    initialSyncDone: false,
    lastUrlThreadId: undefined,
    lastMainThreadId: undefined,
    lastRemoteId: undefined,
    threadNotFound: false,
    isSwitchingThread: false,
  });

  const [threadNotFound, setThreadNotFound] = useState(false);
  const [isSwitchingThread, setIsSwitchingThread] = useState(false);

  // Initial sync: URL -> Runtime (only once when threads load)
  useEffect(() => {
    if (isLoading || syncState.current.initialSyncDone) {
      return;
    }

    syncState.current.initialSyncDone = true;
    syncState.current.lastUrlThreadId = urlThreadId;
    syncState.current.lastMainThreadId = mainThreadId;

    if (urlThreadId && threadIds.includes(urlThreadId) && mainThreadId !== urlThreadId) {
      // Thread is in the local list, switch to it
      syncState.current.isSwitchingThread = true;
      setIsSwitchingThread(true);
      runtime.threadList
        .switchToThread(urlThreadId)
        .then(() => {
          syncState.current.isSwitchingThread = false;
          setIsSwitchingThread(false);
          setThreadNotFound(false);
        })
        .catch(() => {
          syncState.current.isSwitchingThread = false;
          setIsSwitchingThread(false);
        });
    } else if (urlThreadId && !threadIds.includes(urlThreadId)) {
      // Thread doesn't exist in local list, try to fetch it directly
      syncState.current.isSwitchingThread = true;
      setIsSwitchingThread(true);
      api
        .getThread(urlThreadId)
        .then((thread) => {
          if (thread) {
            // Thread exists on server, switch to it
            return runtime.threadList.switchToThread(urlThreadId).then(() => {
              syncState.current.isSwitchingThread = false;
              setIsSwitchingThread(false);
              setThreadNotFound(false);
            });
          } else {
            // Thread truly doesn't exist
            syncState.current.isSwitchingThread = false;
            setIsSwitchingThread(false);
            syncState.current.threadNotFound = true;
            setThreadNotFound(true);
          }
        })
        .catch(() => {
          syncState.current.isSwitchingThread = false;
          setIsSwitchingThread(false);
          syncState.current.threadNotFound = true;
          setThreadNotFound(true);
        });
    } else {
      setThreadNotFound(false);
    }
  }, [isLoading, urlThreadId, mainThreadId, threadIds, runtime.threadList, onThreadChange]);

  // Runtime -> URL: When user clicks a thread or remoteId becomes available, update URL
  useEffect(() => {
    if (isLoading || !syncState.current.initialSyncDone) {
      return;
    }

    // Check if remoteId just became available for a local thread
    // This happens when a new thread gets persisted after first message
    if (
      currentRemoteId &&
      currentRemoteId !== syncState.current.lastRemoteId &&
      mainThreadId?.startsWith("__") &&
      urlThreadId === undefined // currently on /new
    ) {
      syncState.current.lastRemoteId = currentRemoteId;
      syncState.current.lastUrlThreadId = currentRemoteId;
      setThreadNotFound(false);
      onThreadChange(currentRemoteId);
      return;
    }

    // Skip if main thread hasn't changed
    if (mainThreadId === syncState.current.lastMainThreadId) {
      return;
    }

    syncState.current.lastMainThreadId = mainThreadId;

    // New local thread (not persisted yet) - navigate to /new
    if (mainThreadId && mainThreadId.startsWith("__")) {
      syncState.current.lastUrlThreadId = undefined;
      syncState.current.lastRemoteId = undefined;
      setThreadNotFound(false);
      onThreadChange(null);
      return;
    }

    // Only update URL for persisted threads
    if (mainThreadId && mainThreadId !== urlThreadId) {
      syncState.current.lastUrlThreadId = mainThreadId;
      setThreadNotFound(false);
      onThreadChange(mainThreadId);
    }
  }, [mainThreadId, urlThreadId, isLoading, onThreadChange, currentRemoteId]);

  // Reset threadNotFound and switching state when URL changes
  useEffect(() => {
    if (urlThreadId !== syncState.current.lastUrlThreadId) {
      syncState.current.initialSyncDone = false;
      syncState.current.threadNotFound = false;
      syncState.current.isSwitchingThread = false;
      syncState.current.lastRemoteId = undefined;
      setThreadNotFound(false);
      setIsSwitchingThread(false);
    }
  }, [urlThreadId]);

  return {
    isLoadingThread: isLoading || isSwitchingThread || (!!urlThreadId && !syncState.current.initialSyncDone),
    threadNotFound,
  };
};
