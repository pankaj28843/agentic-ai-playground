export type ThreadStatus = "regular" | "archived";

export type MessagePart = {
  type: string;
  [key: string]: unknown;
};

export type ThreadMessage = {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: MessagePart[];
  createdAt: string;
  phoenixTraceId?: string;
  phoenixTraceUrl?: string; // Full URL to Phoenix trace view
  phoenixSessionUrl?: string; // Full URL to Phoenix session view
  runProfile?: string;
  runMode?: string;
  executionMode?: string;
  entrypointReference?: string;
  modelId?: string;
  phoenixSessionId?: string;
  sessionEntryId?: string;
};

export type ThreadSummary = {
  remoteId: string;
  title?: string;
  status: ThreadStatus;
};

export type ThreadDetail = {
  remoteId: string;
  title?: string;
  status: ThreadStatus;
  createdAt: string;
  updatedAt: string;
};

export type ThreadListResponse = {
  threads: ThreadSummary[];
};

export type ProfileSummary = {
  id: string;
  name: string;
  description?: string | null;
  entrypointType?: string | null;
  entrypointReference?: string | null;
  default?: boolean;
  metadata?: Record<string, unknown>;
};

export type ProfilesResponse = {
  profiles: ProfileSummary[];
  runModes: string[];
  defaultRunMode?: string | null;
};

export type PhoenixConfig = {
  enabled: boolean;
  baseUrl?: string;
  projectName?: string;
  projectId?: string;
};

export type SessionEntryView = {
  id: string;
  parentId?: string | null;
  type: string;
  timestamp: string;
  label?: string | null;
  messageRole?: string | null;
  messagePreview?: string | null;
  summary?: string | null;
  customType?: string | null;
  fromId?: string | null;
  details?: Record<string, unknown> | null;
};

export type SessionTreeResponse = {
  sessionId: string;
  header: {
    id: string;
    timestamp: string;
    cwd?: string | null;
    parentSession?: string | null;
  };
  entries: SessionEntryView[];
  roots: string[];
  children: Record<string, string[]>;
  leafId?: string | null;
};

/**
 * Phoenix trace metadata emitted during streaming.
 */
export type PhoenixTraceMetadata = {
  traceId?: string;
  sessionId?: string;
};

/**
 * Runtime metadata emitted during streaming (on final chunk).
 */
export type RuntimeMetadata = {
  runMode?: string;
  profileName?: string;
  modelId?: string;
  executionMode?: string;
  entrypointReference?: string;
};

// Event emitter for Phoenix trace metadata
type PhoenixMetadataListener = (metadata: PhoenixTraceMetadata) => void;
const phoenixListeners = new Set<PhoenixMetadataListener>();

export const phoenixMetadataEvents = {
  subscribe: (listener: PhoenixMetadataListener): (() => void) => {
    phoenixListeners.add(listener);
    return () => {
      phoenixListeners.delete(listener);
    };
  },
  emit: (metadata: PhoenixTraceMetadata): void => {
    phoenixListeners.forEach((listener) => listener(metadata));
  },
};

// Event emitter for runtime metadata
type RuntimeMetadataListener = (metadata: RuntimeMetadata) => void;
const runtimeListeners = new Set<RuntimeMetadataListener>();

export const runtimeMetadataEvents = {
  subscribe: (listener: RuntimeMetadataListener): (() => void) => {
    runtimeListeners.add(listener);
    return () => {
      runtimeListeners.delete(listener);
    };
  },
  emit: (metadata: RuntimeMetadata): void => {
    runtimeListeners.forEach((listener) => listener(metadata));
  },
};

export type ThreadMessagesResponse = {
  messages: ThreadMessage[];
};

export type ChatRunRequest = {
  messages: ThreadMessage[];
  threadId?: string;
  profile?: string;
  runMode?: string;
};

/**
 * Validate that remoteId is a non-empty string.
 * Throws an error if remoteId is undefined, null, not a string, or empty.
 */
function requireRemoteId(remoteId: unknown, operation: string): void {
  if (remoteId === undefined || remoteId === null || typeof remoteId !== "string") {
    throw new Error(`${operation}: remoteId is required but got "${String(remoteId)}"`);
  }

  const trimmed = remoteId.trim();
  if (!trimmed || trimmed === "undefined" || trimmed === "null") {
    throw new Error(`${operation}: remoteId is required but got "${remoteId}"`);
  }
}

export class ApiClient {
  readonly baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async listThreads(): Promise<ThreadListResponse> {
    return this.getJson("/api/threads");
  }

  async getThread(remoteId: string): Promise<ThreadDetail | null> {
    requireRemoteId(remoteId, "getThread");
    try {
      return await this.getJson(`/api/threads/${remoteId}`);
    } catch {
      return null;
    }
  }

  async listProfiles(): Promise<ProfilesResponse> {
    return this.getJson("/api/profiles");
  }

  async getPhoenixConfig(): Promise<PhoenixConfig> {
    try {
      return await this.getJson("/api/phoenix");
    } catch {
      return { enabled: false };
    }
  }

  async createThread(): Promise<{ remoteId: string }> {
    return this.postJson("/api/threads", {});
  }

  async renameThread(remoteId: string, title: string): Promise<void> {
    requireRemoteId(remoteId, "renameThread");
    await this.patchJson(`/api/threads/${remoteId}`, { title });
  }

  async archiveThread(remoteId: string): Promise<void> {
    requireRemoteId(remoteId, "archiveThread");
    await this.postJson(`/api/threads/${remoteId}/archive`, {});
  }

  async unarchiveThread(remoteId: string): Promise<void> {
    requireRemoteId(remoteId, "unarchiveThread");
    await this.postJson(`/api/threads/${remoteId}/unarchive`, {});
  }

  async deleteThread(remoteId: string): Promise<void> {
    requireRemoteId(remoteId, "deleteThread");
    await this.deleteJson(`/api/threads/${remoteId}`);
  }

  async generateTitle(remoteId: string, messages: ThreadMessage[]): Promise<string> {
    requireRemoteId(remoteId, "generateTitle");
    const response = await this.postJson<{ title?: string }>(`/api/threads/${remoteId}/title`, {
      messages,
    });
    return response.title ?? "";
  }

  async getMessages(remoteId: string): Promise<ThreadMessagesResponse> {
    requireRemoteId(remoteId, "getMessages");
    return this.getJson(`/api/threads/${remoteId}/messages`);
  }

  async appendMessage(
    remoteId: string,
    message: ThreadMessage,
    phoenixTraceId?: string,
    runtimeMetadata?: RuntimeMetadata,
    phoenixSessionId?: string,
    parentSessionEntryId?: string,
  ): Promise<void> {
    requireRemoteId(remoteId, "appendMessage");
    await this.postJson(`/api/threads/${remoteId}/messages`, {
      message,
      phoenixTraceId,
      phoenixSessionId,
      runProfile: runtimeMetadata?.profileName,
      runMode: runtimeMetadata?.runMode,
      executionMode: runtimeMetadata?.executionMode,
      entrypointReference: runtimeMetadata?.entrypointReference,
      modelId: runtimeMetadata?.modelId,
      parentSessionEntryId,
    });
  }

  async getSessionTree(remoteId: string): Promise<SessionTreeResponse> {
    requireRemoteId(remoteId, "getSessionTree");
    return this.getJson(`/api/threads/${remoteId}/session-tree`);
  }

  async labelSessionEntry(
    remoteId: string,
    entryId: string,
    label: string | null,
  ): Promise<{ status: string; labelEntryId: string }> {
    requireRemoteId(remoteId, "labelSessionEntry");
    return this.postJson(`/api/threads/${remoteId}/session-tree/label`, {
      entryId,
      label,
    });
  }

  async runChat(request: ChatRunRequest, signal?: AbortSignal): Promise<Response> {
    return fetch(`${this.baseUrl}/api/chat/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json() as Promise<T>;
  }

  private async postJson<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json() as Promise<T>;
  }

  private async patchJson(path: string, body: unknown): Promise<void> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
  }

  private async deleteJson(path: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
  }
}
