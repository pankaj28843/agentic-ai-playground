import type { CSSProperties, FC } from "react";
import { useEffect, useMemo, useState } from "react";
import { useAssistantApi } from "@assistant-ui/react";
import { ChevronRight, RefreshCw, X } from "lucide-react";

import { useSessionTree } from "../contexts/SessionTreeContext";
import styles from "./SessionTreePanel.module.css";

const buildTitle = (entry: { label?: string | null; summary?: string | null; messagePreview?: string | null }) => {
  return entry.label || entry.summary || entry.messagePreview || "Untitled entry";
};

export const SessionTreePanel: FC = () => {
  const api = useAssistantApi();
  const {
    threadId,
    tree,
    entriesById,
    activeEntryId,
    setActiveEntryId,
    refresh,
    labelEntry,
    isLoading,
    error,
  } = useSessionTree();
  const [labelValue, setLabelValue] = useState("");

  const activeEntry = activeEntryId ? entriesById[activeEntryId] : null;
  const orderedRoots = useMemo(() => tree?.roots ?? [], [tree]);

  useEffect(() => {
    if (!activeEntry) {
      setLabelValue("");
      return;
    }
    setLabelValue(activeEntry.label ?? "");
  }, [activeEntry]);

  const handleInsertSummary = (summary?: string | null) => {
    if (!summary) {
      return;
    }
    api.composer().setText(summary.trim());
  };

  const renderNode = (entryId: string, depth: number) => {
    const entry = entriesById[entryId];
    if (!entry) {
      return null;
    }
    const children = tree?.children?.[entryId] ?? [];
    const isActive = entryId === activeEntryId;
    const title = buildTitle(entry);

    return (
      <div key={entryId} className={styles.nodeWrapper} style={{ "--depth": depth } as CSSProperties}>
        <button
          type="button"
          className={`${styles.nodeRow} ${isActive ? styles.nodeActive : ""}`}
          onClick={() => setActiveEntryId(entryId)}
        >
          <ChevronRight aria-hidden="true" className={styles.nodeChevron} />
          <div className={styles.nodeContent}>
            <span className={styles.nodeTitle}>{title}</span>
            <span className={styles.nodeMeta}>{entry.type}</span>
          </div>
        </button>
        {entry.summary && (
          <button
            type="button"
            className={styles.nodeAction}
            onClick={() => handleInsertSummary(entry.summary)}
          >
            Insert summary
          </button>
        )}
        {children.map((childId) => renderNode(childId, depth + 1))}
      </div>
    );
  };

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <div>
          <p className={styles.panelEyebrow}>Session Tree</p>
          <h3 className={styles.panelTitle}>Branch navigation</h3>
        </div>
        <button type="button" className={styles.panelRefresh} onClick={() => refresh()}>
          <RefreshCw aria-hidden="true" />
          Refresh
        </button>
      </header>

      {!threadId && <p className={styles.panelHint}>Start a thread to build a session tree.</p>}
      {threadId && isLoading && <p className={styles.panelHint}>Loading tree...</p>}
      {threadId && error && <p className={styles.panelHint}>{error}</p>}

      {threadId && tree && tree.entries.length === 0 && !isLoading && (
        <p className={styles.panelHint}>No entries yet. Send a message to begin.</p>
      )}

      {threadId && tree && tree.entries.length > 0 && (
        <div className={styles.tree}>{orderedRoots.map((rootId) => renderNode(rootId, 0))}</div>
      )}

      {activeEntry && (
        <div className={styles.activePanel}>
          <div className={styles.activeHeader}>
            <div>
              <p className={styles.activeEyebrow}>Active branch</p>
              <p className={styles.activeTitle}>{buildTitle(activeEntry)}</p>
            </div>
            <button
              type="button"
              className={styles.activeClear}
              onClick={() => setActiveEntryId(null)}
            >
              <X aria-hidden="true" />
              Clear
            </button>
          </div>
          <label className={styles.labelRow}>
            <span>Label</span>
            <input
              value={labelValue}
              onChange={(event) => setLabelValue(event.target.value)}
              placeholder="Add a checkpoint name"
            />
          </label>
          <button
            type="button"
            className={styles.labelSave}
            onClick={() => void labelEntry(activeEntry.id, labelValue || null)}
          >
            Save label
          </button>
        </div>
      )}
    </section>
  );
};
