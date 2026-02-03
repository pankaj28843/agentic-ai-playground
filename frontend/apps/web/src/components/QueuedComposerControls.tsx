import { useAssistantApi, useAssistantState, ComposerPrimitive } from "@assistant-ui/react";
import { ArrowUp, CornerDownLeft, CornerUpLeft, Square } from "lucide-react";
import type { FC } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useResources } from "../contexts/ResourcesContext";
import { parseCommand, resolveCommand } from "../utils/commands";
import styles from "./ThreadView.module.css";

type QueueMode = "steer" | "follow-up";

interface QueueItem {
  text: string;
  mode: QueueMode;
}

export const QueuedComposerControls: FC = () => {
  const api = useAssistantApi();
  const isRunning = useAssistantState(({ thread }) => thread.isRunning);
  const composerText = useAssistantState(({ composer }) => composer.text);
  const attachmentCount = useAssistantState(({ composer }) => composer.attachments.length);
  const { resources, enabledPrompts, enabledSkills } = useResources();

  const [queue, setQueue] = useState<QueueItem[]>([]);
  const queueRef = useRef(queue);
  const wasRunningRef = useRef(isRunning);
  const [warning, setWarning] = useState<string | null>(null);

  useEffect(() => {
    queueRef.current = queue;
  }, [queue]);

  const enqueue = useCallback(
    (mode: QueueMode) => {
      if (!composerText && attachmentCount === 0) {
        return;
      }
      if (attachmentCount > 0) {
        setWarning("Attachments cannot be queued yet.");
        return;
      }
      const parsed = parseCommand(composerText);
      const enabled = parsed?.type === "prompt" ? enabledPrompts : enabledSkills;
      const commandResolution = resolveCommand(composerText, resources, enabled);
      if (commandResolution.error) {
        setWarning(commandResolution.error);
        return;
      }
      setWarning(null);
      setQueue((prev) => [
        ...prev,
        { text: commandResolution.applied ? commandResolution.resolvedText : composerText, mode },
      ]);
      api.composer().reset();
      if (mode === "steer") {
        api.thread().cancelRun();
      }
    },
    [api, attachmentCount, composerText, enabledPrompts, enabledSkills, resources],
  );

  useEffect(() => {
    const wasRunning = wasRunningRef.current;
    wasRunningRef.current = isRunning;
    if (!wasRunning || isRunning) {
      return;
    }
    const next = queueRef.current[0];
    if (!next) {
      return;
    }
    setQueue((prev) => prev.slice(1));
    api.composer().setText(next.text);
    api.composer().send();
  }, [api, isRunning]);

  return (
    <div className={styles.composerQueueControls}>
      {!isRunning && (
        <button
          className={styles.composerSend}
          type="button"
          onClick={() => {
            const parsed = parseCommand(composerText);
            const enabled = parsed?.type === "prompt" ? enabledPrompts : enabledSkills;
            const commandResolution = resolveCommand(composerText, resources, enabled);
            if (commandResolution.error) {
              setWarning(commandResolution.error);
              return;
            }
            setWarning(null);
            if (commandResolution.applied) {
              api.composer().setText(commandResolution.resolvedText);
            }
            api.composer().send();
          }}
        >
          <ArrowUp aria-hidden="true" />
          Send
        </button>
      )}
      {isRunning && (
        <div className={styles.composerQueueRunning}>
          <ComposerPrimitive.Cancel asChild>
            <button className={styles.composerCancel} type="button">
              <Square aria-hidden="true" />
              Stop
            </button>
          </ComposerPrimitive.Cancel>
          <button
            className={styles.composerQueueBtn}
            type="button"
            onClick={() => enqueue("steer")}
          >
            <CornerUpLeft aria-hidden="true" />
            Steer
          </button>
          <button
            className={styles.composerQueueBtn}
            type="button"
            onClick={() => enqueue("follow-up")}
          >
            <CornerDownLeft aria-hidden="true" />
            Follow-up
          </button>
        </div>
      )}
      {(queue.length > 0 || warning) && (
        <div className={styles.composerQueueIndicator} role="status">
          {queue.length > 0 && <span>{queue.length} queued</span>}
          {warning && <span className={styles.composerQueueWarning}>{warning}</span>}
        </div>
      )}
    </div>
  );
};
