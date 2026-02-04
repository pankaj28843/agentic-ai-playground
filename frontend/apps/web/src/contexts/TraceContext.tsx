import { createActorContext } from "@xstate/react";
import type { FC, ReactNode } from "react";
import { useEffect } from "react";
import { useSearchParams } from "react-router-dom";

import {
  phoenixMetadataEvents,
  runtimeMetadataEvents,
  type PhoenixTraceMetadata,
  type RuntimeMetadata,
} from "@agentic-ai-playground/api-client";

import type { TraceItem } from "../components/TracePanel";
import {
  traceMachine,
  type PhoenixMetadata,
  type TraceContext as TraceContextState,
} from "../state/traceMachine";

interface TraceContextValue {
  trace: TraceContextState["trace"];
  expandedItems: Set<number>;
  fullOutputItems: Set<number>;
  openTrace: (params: {
    items: TraceItem[];
    status: "running" | "complete";
    startTime?: string;
    messageId: string;
    phoenix?: PhoenixMetadata;
    runtime?: RuntimeMetadata;
  }) => void;
  closeTrace: () => void;
  updateTrace: (params: {
    items?: TraceItem[];
    status?: "running" | "complete";
    startTime?: string;
    phoenix?: PhoenixMetadata;
    runtime?: RuntimeMetadata;
  }) => void;
  toggleItemExpanded: (index: number) => void;
  toggleItemOutput: (index: number) => void;
}

const TraceActorContext = createActorContext(traceMachine);

export const TraceProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTraceId = searchParams.get("trace_id");

  return (
    <TraceActorContext.Provider
      logic={traceMachine}
      options={{ input: { initialTraceId } }}
    >
      <TraceBridge setSearchParams={setSearchParams} />
      {children}
    </TraceActorContext.Provider>
  );
};

const TraceBridge = ({
  setSearchParams,
}: {
  setSearchParams: ReturnType<typeof useSearchParams>[1];
}) => {
  const actorRef = TraceActorContext.useActorRef();
  const trace = TraceActorContext.useSelector((state) => state.context.trace);

  useEffect(() => {
    const traceId = trace.isOpen ? trace.messageId : null;
    const currentPath = window.location.pathname;
    if (!currentPath.startsWith("/c/")) {
      return;
    }
    setSearchParams((prev) => {
      const newParams = new URLSearchParams(prev);
      if (traceId) {
        newParams.set("trace_id", traceId);
      } else {
        newParams.delete("trace_id");
      }
      return newParams;
    }, { replace: true });
  }, [setSearchParams, trace.isOpen, trace.messageId]);

  useEffect(() => {
    const unsubscribe = phoenixMetadataEvents.subscribe((metadata: PhoenixTraceMetadata) => {
      actorRef.send({ type: "PHOENIX.METADATA", metadata });
    });
    return unsubscribe;
  }, [actorRef]);

  useEffect(() => {
    const unsubscribe = runtimeMetadataEvents.subscribe((metadata: RuntimeMetadata) => {
      actorRef.send({ type: "RUNTIME.METADATA", metadata });
    });
    return unsubscribe;
  }, [actorRef]);

  useEffect(() => {
    const traceId = trace.messageId;
    if (traceId && trace.isOpen) {
      return;
    }
    if (traceId && !trace.isOpen) {
      actorRef.send({ type: "TRACE.RESTORE", messageId: traceId });
    }
  }, [actorRef, trace.isOpen, trace.messageId]);

  return null;
};

export const useTrace = (): TraceContextValue => {
  const actorRef = TraceActorContext.useActorRef();
  const trace = TraceActorContext.useSelector((state) => state.context.trace);
  const expandedItems = TraceActorContext.useSelector((state) => state.context.expandedItems);
  const fullOutputItems = TraceActorContext.useSelector((state) => state.context.fullOutputItems);

  return {
    trace,
    expandedItems,
    fullOutputItems,
    openTrace: (params) => actorRef.send({ type: "TRACE.OPEN", ...params }),
    closeTrace: () => actorRef.send({ type: "TRACE.CLOSE" }),
    updateTrace: (params) => actorRef.send({ type: "TRACE.UPDATE", ...params }),
    toggleItemExpanded: (index) => actorRef.send({ type: "TRACE.TOGGLE_EXPANDED", index }),
    toggleItemOutput: (index) => actorRef.send({ type: "TRACE.TOGGLE_FULL_OUTPUT", index }),
  };
};
