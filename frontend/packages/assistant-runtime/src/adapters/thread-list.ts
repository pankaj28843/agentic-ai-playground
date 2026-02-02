/**
 * Thread list adapter for managing threads via the backend API.
 */

import type { unstable_RemoteThreadListAdapter as RemoteThreadListAdapter } from "@assistant-ui/react";
import { createAssistantStream } from "assistant-stream";
import { api } from "./chat-model";
import { toApiMessage } from "../converters";
import { ThreadAdapterProvider } from "./thread-history";

/**
 * Adapter for managing remote threads via the API.
 */
export const threadListAdapter: RemoteThreadListAdapter = {
  async list() {
    return api.listThreads();
  },

  async initialize() {
    const { remoteId } = await api.createThread();
    return { remoteId, externalId: undefined };
  },

  async rename(remoteId, title) {
    await api.renameThread(remoteId, title);
  },

  async archive(remoteId) {
    await api.archiveThread(remoteId);
  },

  async unarchive(remoteId) {
    await api.unarchiveThread(remoteId);
  },

  async delete(remoteId) {
    await api.deleteThread(remoteId);
  },

  async fetch(remoteId) {
    const thread = await api.getThread(remoteId);
    if (!thread) {
      throw new Error("Thread not found");
    }
    return {
      remoteId: thread.remoteId,
      title: thread.title,
      status: thread.status,
    };
  },

  async generateTitle(remoteId, messages) {
    return createAssistantStream(async (controller) => {
      const title = await api.generateTitle(remoteId, messages.map(toApiMessage));
      controller.appendText(title || "New chat");
    });
  },

  unstable_Provider: ThreadAdapterProvider,
};
