import {
  ActionBarPrimitive,
  AttachmentPrimitive,
  AuiIf,
  ComposerPrimitive,
  ErrorPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  useMessage,
} from "@assistant-ui/react";
import {
  ArrowDown,
  Check,
  Copy,
  FileText,
  Paperclip,
  Pencil,
  RefreshCw,
  X,
} from "lucide-react";
import type { FC } from "react";
import { useEffect, useId } from "react";

import { useTrace } from "../contexts/TraceContext";
import { MarkdownText } from "./MarkdownText";
import { QueuedComposerControls } from "./QueuedComposerControls";
import { SlashCommandMenu } from "./SlashCommandMenu";
import { TraceIndicator, type TraceItem } from "./TracePanel";
import styles from "./ThreadView.module.css";

export const ThreadView: FC = () => {
  return (
    <ThreadPrimitive.Root className={styles.threadRoot}>
      <ThreadPrimitive.Viewport className={styles.threadViewport} turnAnchor="top">
        <AuiIf condition={({ thread }) => thread.isEmpty}>
          <ThreadWelcome />
        </AuiIf>
        <ThreadPrimitive.Messages components={{ AssistantMessage, UserMessage, EditComposer }} />
      </ThreadPrimitive.Viewport>
      <ThreadScrollToBottom />
      <ThreadPrimitive.ViewportFooter className={styles.threadFooter}>
        <Composer />
      </ThreadPrimitive.ViewportFooter>
    </ThreadPrimitive.Root>
  );
};

const ThreadScrollToBottom: FC = () => {
  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <button className={styles.scrollToBottom} type="button">
        <ArrowDown aria-hidden="true" />
        Jump to latest
      </button>
    </ThreadPrimitive.ScrollToBottom>
  );
};

const ThreadWelcome: FC = () => {
  return (
    <div className={styles.threadWelcome}>
      <div className={styles.threadWelcomeCard}>
        <p className={styles.eyebrow}>Assistant UI Playground</p>
        <h1>Start a new run</h1>
        <p>
          Ask a question, inspect streaming updates, and keep your threads safely stored on disk.
        </p>
      </div>
      <div className={styles.threadWelcomeHint}>
        Tip: use the thread list on the left to keep parallel explorations.
      </div>
    </div>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className={styles.composer}>
      <ComposerPrimitive.AttachmentDropzone className={styles.composerDropzone}>
        <ComposerAttachments />
        <ComposerPrimitive.Input
          className={styles.composerInput}
          placeholder="Send a message..."
          rows={1}
        />
        <SlashCommandMenu />
        <div className={styles.composerActions}>
          <ComposerAddAttachment />
          <QueuedComposerControls />
        </div>
      </ComposerPrimitive.AttachmentDropzone>
    </ComposerPrimitive.Root>
  );
};

const AssistantMessage: FC = () => {
  const reactMessageId = useId();
  const { trace, openTrace, updateTrace } = useTrace();
  const message = useMessage((state) => state);
  const status = message?.status?.type ?? "complete";

  // Get actual message ID and metadata (MessageState is ThreadMessage & extras)
  const messageId = message?.id ?? reactMessageId;
  const metadata = message?.metadata?.custom as {
    phoenixTraceId?: string;
    phoenixTraceUrl?: string;
    phoenixSessionId?: string;
    phoenixSessionUrl?: string;
    runProfile?: string;
    runMode?: string;
    executionMode?: string;
    entrypointReference?: string;
    modelId?: string;
  } | undefined;

  // Extract trace items from message content
  const traceItems: TraceItem[] = [];
  const content = message?.content ?? [];
  let earliestTimestamp: string | undefined;

  for (const part of content) {
    if (part.type === "reasoning" && "text" in part) {
      const partWithTimestamp = part as { text?: string; timestamp?: string };
      if (partWithTimestamp.timestamp && (!earliestTimestamp || partWithTimestamp.timestamp < earliestTimestamp)) {
        earliestTimestamp = partWithTimestamp.timestamp;
      }
      traceItems.push({
        type: "thinking",
        text: String(partWithTimestamp.text ?? ""),
        timestamp: partWithTimestamp.timestamp,
      });
    } else if (part.type === "tool-call") {
      // Access status from part safely with type assertion
      const partWithStatus = part as {
        toolName?: string;
        args?: unknown;
        argsText?: string;
        result?: unknown;
        status?: { type?: string };
        isError?: boolean;
        timestamp?: string;
        callingAgent?: string;
      };
      if (partWithStatus.timestamp && (!earliestTimestamp || partWithStatus.timestamp < earliestTimestamp)) {
        earliestTimestamp = partWithStatus.timestamp;
      }
      // Parse args from argsText if available, otherwise use args
      let parsedArgs: Record<string, unknown> = {};
      if (partWithStatus.argsText) {
        try {
          parsedArgs = JSON.parse(partWithStatus.argsText);
        } catch {
          parsedArgs = { _raw: partWithStatus.argsText };
        }
      } else if (partWithStatus.args && typeof partWithStatus.args === "object") {
        parsedArgs = partWithStatus.args as Record<string, unknown>;
      }
      traceItems.push({
        type: "tool-call",
        toolName: String(partWithStatus.toolName ?? "unknown"),
        args: parsedArgs,
        result: partWithStatus.result,
        resultFull: (partWithStatus as { resultFull?: unknown }).resultFull,
        resultTruncated: (partWithStatus as { resultTruncated?: boolean }).resultTruncated,
        status: partWithStatus.status?.type ?? "complete",
        isError: !!partWithStatus.isError,
        timestamp: partWithStatus.timestamp,
        callingAgent: partWithStatus.callingAgent,
      });
    } else if (part.type === "text" && "text" in part) {
      // Extract <thinking> blocks from text parts ONLY if we don't have reasoning parts
      // (Backend now extracts thinking blocks as reasoning parts with timestamps)
      const hasReasoningParts = content.some((p) => p.type === "reasoning");
      if (!hasReasoningParts) {
        const text = String(part.text ?? "");
        const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/g;
        let match;
        while ((match = thinkingRegex.exec(text)) !== null) {
          traceItems.push({ type: "thinking", text: match[1].trim() });
        }
      }
    } else if ((part as { type: string }).type === "agent-event") {
      // Handle multi-agent orchestration events (graph/swarm mode)
      const agentPart = part as {
        agentName?: string;
        eventType?: string;
        fromAgents?: string[];
        toAgents?: string[];
        handoffMessage?: string;
        timestamp?: string;
      };
      if (agentPart.timestamp && (!earliestTimestamp || agentPart.timestamp < earliestTimestamp)) {
        earliestTimestamp = agentPart.timestamp;
      }
      traceItems.push({
        type: "agent-event",
        agentName: agentPart.agentName,
        eventType: (agentPart.eventType as "start" | "complete" | "handoff") ?? "start",
        fromAgents: agentPart.fromAgents,
        toAgents: agentPart.toAgents,
        handoffMessage: agentPart.handoffMessage,
        timestamp: agentPart.timestamp,
      });
    }
  }

  const thinkingCount = traceItems.filter((item) => item.type === "thinking").length;
  const toolCallCount = traceItems.filter((item) => item.type === "tool-call").length;
  const agentEventCount = traceItems.filter((item) => item.type === "agent-event").length;

  // Keep trace panel updated if this message's trace is currently open
  // This also handles restoring phoenix metadata after page reload
  const isThisTraceOpen = trace.isOpen && trace.messageId === messageId;
  useEffect(() => {
    if (isThisTraceOpen) {
      updateTrace({
        items: traceItems,
        status: status === "running" ? "running" : "complete",
        startTime: earliestTimestamp,
        // Always pass phoenix metadata so it's restored after page reload
        phoenix: metadata ? {
          traceId: metadata.phoenixTraceId,
          sessionId: metadata.phoenixSessionId,
          traceUrl: metadata.phoenixTraceUrl,
          sessionUrl: metadata.phoenixSessionUrl,
        } : undefined,
        // Always pass runtime metadata so it's restored after page reload
        runtime: metadata ? {
          runMode: metadata.runMode,
          profileName: metadata.runProfile,
          modelId: metadata.modelId,
          executionMode: metadata.executionMode,
          entrypointReference: metadata.entrypointReference,
        } : undefined,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only update when trace data changes
  }, [isThisTraceOpen, traceItems.length, status, earliestTimestamp, metadata?.phoenixTraceUrl, metadata?.runMode]);

  const handleOpenTrace = () => {
    openTrace({
      items: traceItems,
      status: status === "running" ? "running" : "complete",
      startTime: earliestTimestamp,
      messageId,
      // Pass phoenix URLs from message metadata
      phoenix: metadata ? {
        traceId: metadata.phoenixTraceId,
        sessionId: metadata.phoenixSessionId,
        traceUrl: metadata.phoenixTraceUrl,
        sessionUrl: metadata.phoenixSessionUrl,
      } : undefined,
      // Pass runtime metadata
      runtime: metadata ? {
        runMode: metadata.runMode,
        profileName: metadata.runProfile,
        modelId: metadata.modelId,
        executionMode: metadata.executionMode,
        entrypointReference: metadata.entrypointReference,
      } : undefined,
    });
  };

  return (
    <MessagePrimitive.Root className={`${styles.message} ${styles.messageAssistant}`} data-role="assistant">
      <div className={styles.messageAvatar}>AI</div>
      <div className={styles.messageBody}>
        <MessageMeta label="Assistant" />
        {(thinkingCount > 0 || toolCallCount > 0 || agentEventCount > 0) && (
          <TraceIndicator
            thinkingCount={thinkingCount}
            toolCallCount={toolCallCount}
            agentEventCount={agentEventCount}
            onClick={handleOpenTrace}
            isRunning={status === "running"}
          />
        )}
        <MessagePrimitive.Parts
          components={{
            Text: MarkdownText,
            // Hide tool calls and reasoning inline - they're shown in the trace panel
            Reasoning: HiddenPart,
            tools: { Override: HiddenPart },
          }}
        />
        <MessageError />
        <AssistantActionBar />
      </div>
    </MessagePrimitive.Root>
  );
};

const AssistantActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className={styles.actionBar}
    >
      <ActionBarPrimitive.Copy className={styles.actionBtn} aria-label="Copy message">
        <span className={styles.actionIconCopied}><Check aria-hidden="true" /></span>
        <span className={styles.actionIconDefault}><Copy aria-hidden="true" /></span>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Reload asChild>
        <button className={styles.actionBtn} type="button" aria-label="Regenerate response">
          <RefreshCw aria-hidden="true" />
        </button>
      </ActionBarPrimitive.Reload>
    </ActionBarPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className={`${styles.message} ${styles.messageUser}`} data-role="user">
      <div className={styles.messageBody}>
        <MessageMeta label="You" />
        <UserMessageAttachments />
        <MessagePrimitive.Parts />
        <UserActionBar />
      </div>
      <div className={styles.messageAvatar}>You</div>
    </MessagePrimitive.Root>
  );
};

const UserMessageAttachments: FC = () => {
  return (
    <MessagePrimitive.If hasAttachments>
      <div className={styles.messageAttachments}>
        <MessagePrimitive.Attachments
          components={{ Attachment: MessageAttachmentTile }}
        />
      </div>
    </MessagePrimitive.If>
  );
};

const MessageAttachmentTile: FC = () => {
  return (
    <AttachmentPrimitive.Root className={styles.messageAttachmentTile}>
      <AttachmentThumb />
    </AttachmentPrimitive.Root>
  );
};

const UserActionBar: FC = () => {
  return (
    <ActionBarPrimitive.Root
      hideWhenRunning
      autohide="not-last"
      className={styles.actionBar}
    >
      <ActionBarPrimitive.Copy className={styles.actionBtn} aria-label="Copy message">
        <span className={styles.actionIconCopied}><Check aria-hidden="true" /></span>
        <span className={styles.actionIconDefault}><Copy aria-hidden="true" /></span>
      </ActionBarPrimitive.Copy>
      <ActionBarPrimitive.Edit asChild>
        <button className={styles.actionBtn} type="button" aria-label="Edit message">
          <Pencil aria-hidden="true" />
        </button>
      </ActionBarPrimitive.Edit>
    </ActionBarPrimitive.Root>
  );
};

const MessageError: FC = () => {
  return (
    <MessagePrimitive.Error>
      <ErrorPrimitive.Root className={styles.messageError}>
        <ErrorPrimitive.Message />
      </ErrorPrimitive.Root>
    </MessagePrimitive.Error>
  );
};

const MessageMeta: FC<{ label: string }> = ({ label }) => {
  const status = useMessage((state) => state?.status?.type ?? "complete");
  const statusLabel = status === "running" ? "thinking" : "done";

  return (
    <div className={styles.messageMeta}>
      <span>{label}</span>
      <span
        className={`${styles.messageStatus} ${
          statusLabel === "thinking" ? styles.messageStatusThinking : ""
        }`}
      >
        {statusLabel}
      </span>
    </div>
  );
};

/**
 * Hidden part component - renders nothing.
 * Used to suppress inline rendering of tool calls and reasoning,
 * since they're displayed in the trace panel instead.
 */
const HiddenPart: FC = () => null;

const EditComposer: FC = () => {
  return (
    <MessagePrimitive.Root className={`${styles.message} ${styles.editComposer}`} data-role="user">
      <ComposerPrimitive.Root className={styles.editComposerRoot}>
        <ComposerPrimitive.Input className={styles.editComposerInput} autoFocus />
        <div className={styles.editComposerActions}>
          <ComposerPrimitive.Cancel asChild>
            <button className={styles.ghost} type="button">
              Cancel
            </button>
          </ComposerPrimitive.Cancel>
          <ComposerPrimitive.Send asChild>
            <button className={styles.primary} type="submit">
              Update
            </button>
          </ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.Root>
    </MessagePrimitive.Root>
  );
};

// Attachment components
const ComposerAddAttachment: FC = () => {
  return (
    <ComposerPrimitive.AddAttachment asChild>
      <button
        className={`${styles.actionBtn} ${styles.attachmentBtn}`}
        type="button"
        aria-label="Add attachment"
      >
        <Paperclip aria-hidden="true" />
      </button>
    </ComposerPrimitive.AddAttachment>
  );
};

const ComposerAttachments: FC = () => {
  return (
    <div className={styles.composerAttachments}>
      <ComposerPrimitive.Attachments
        components={{ Attachment: AttachmentTile }}
      />
    </div>
  );
};

const AttachmentTile: FC = () => {
  return (
    <AttachmentPrimitive.Root className={styles.attachmentTile}>
      <AttachmentThumb />
      <AttachmentPrimitive.Remove asChild>
        <button
          className={styles.attachmentRemove}
          type="button"
          aria-label="Remove attachment"
        >
          <X aria-hidden="true" />
        </button>
      </AttachmentPrimitive.Remove>
    </AttachmentPrimitive.Root>
  );
};

const AttachmentThumb: FC = () => {
  return (
    <div className={styles.attachmentFallback}>
      <FileText aria-hidden="true" />
    </div>
  );
};
