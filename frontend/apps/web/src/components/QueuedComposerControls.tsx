import { useAssistantApi, useAssistantState, ComposerPrimitive } from "@assistant-ui/react";
import { ArrowUp, CornerDownLeft, CornerUpLeft, Square } from "lucide-react";
import type { FC } from "react";
import { useCallback, useEffect } from "react";
import { useMachine } from "@xstate/react";

import { composerQueueMachine, type QueueMode } from "../state/composerQueueMachine";
import styles from "./ThreadView.module.css";

export const QueuedComposerControls: FC = () => {
  const api = useAssistantApi();
  const isRunning = useAssistantState(({ thread }) => thread.isRunning);
  const composerText = useAssistantState(({ composer }) => composer.text);
  const attachmentCount = useAssistantState(({ composer }) => composer.attachments.length);
  const [state, send] = useMachine(composerQueueMachine, { input: {} });
  const { queue, warning, pendingSend, pendingReset, cancelRequested } = state.context;

  const enqueue = useCallback(
    (mode: QueueMode) => {
      send({
        type: "QUEUE.REQUEST",
        mode,
        composerText,
        attachmentCount,
      });
    },
    [attachmentCount, composerText, send],
  );

  useEffect(() => {
    send({ type: "ASSISTANT.RUNNING.CHANGED", isRunning });
  }, [isRunning, send]);

  useEffect(() => {
    if (!pendingReset) {
      return;
    }
    api.composer().reset();
    send({ type: "RESET.ACK" });
  }, [api, pendingReset, send]);

  useEffect(() => {
    if (!cancelRequested) {
      return;
    }
    api.thread().cancelRun();
    send({ type: "CANCEL.ACK" });
  }, [api, cancelRequested, send]);

  useEffect(() => {
    if (!pendingSend) {
      return;
    }
    api.composer().setText(pendingSend.text);
    api.composer().send();
    send({ type: "SEND.DISPATCHED" });
  }, [api, pendingSend, send]);

  return (
    <div className={styles.composerQueueControls}>
      {!isRunning && (
        <button
          className={styles.composerSend}
          type="button"
          onClick={() => {
            send({
              type: "SEND.REQUEST",
              composerText,
              attachmentCount,
            });
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
