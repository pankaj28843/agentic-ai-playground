/**
 * Hook for generating Phoenix deep links.
 */

import { useMemo } from "react";

import { useAppDataSelector } from "../state/appDataContext";

export interface PhoenixDeepLinks {
  /** Whether Phoenix is enabled and configured */
  enabled: boolean;
  /** URL to the trace in Phoenix, or null if not available */
  traceUrl: string | null;
  /** URL to the session in Phoenix, or null if not available */
  sessionUrl: string | null;
  /** Generate a trace URL for a specific trace ID */
  getTraceUrl: (traceId: string) => string | null;
  /** Generate a session URL for a specific session ID */
  getSessionUrl: (sessionId: string) => string | null;
}

/**
 * Hook for generating Phoenix deep links from trace/session IDs.
 *
 * @param traceId - Optional trace ID to generate links for
 * @param sessionId - Optional session ID to generate links for
 * @returns Object with enabled flag and URL generators
 */
export function usePhoenixLinks(traceId?: string, sessionId?: string): PhoenixDeepLinks {
  const config = useAppDataSelector((state) => state.context.phoenixConfig);

  const enabled = config?.enabled ?? false;
  const baseUrl = config?.baseUrl;
  const projectId = config?.projectId;

  const getTraceUrl = useMemo(() => {
    return (id: string): string | null => {
      if (!enabled || !baseUrl || !projectId || !id) {
        return null;
      }
      // Encode trace ID as base64 for Phoenix URL format
      const encodedId = btoa(`Trace:${id}`);
      return `${baseUrl}/projects/${projectId}/traces/${encodedId}`;
    };
  }, [enabled, baseUrl, projectId]);

  const getSessionUrl = useMemo(() => {
    return (id: string): string | null => {
      if (!enabled || !baseUrl || !projectId || !id) {
        return null;
      }
      // Session URL format (sessions page with filter)
      return `${baseUrl}/projects/${projectId}/sessions?sessionId=${encodeURIComponent(id)}`;
    };
  }, [enabled, baseUrl, projectId]);

  const resolvedTraceUrl = traceId ? getTraceUrl(traceId) : null;
  const resolvedSessionUrl = sessionId ? getSessionUrl(sessionId) : null;

  return {
    enabled,
    traceUrl: resolvedTraceUrl,
    sessionUrl: resolvedSessionUrl,
    getTraceUrl,
    getSessionUrl,
  };
}
