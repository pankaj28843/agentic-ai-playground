import { AuiIf, ThreadListItemPrimitive, ThreadListPrimitive } from "@assistant-ui/react";
import { Plus } from "lucide-react";
import type { FC } from "react";
import styles from "./ThreadList.module.css";

export const ThreadList: FC = () => {
  return (
    <ThreadListPrimitive.Root className={styles.threadList}>
      <ThreadListPrimitive.New asChild>
        <button className={styles.threadNew} type="button">
          <Plus aria-hidden="true" />
          New thread
        </button>
      </ThreadListPrimitive.New>
      <AuiIf condition={({ threads }) => threads.isLoading}>
        <div className={styles.threadLoading}>Loading threads...</div>
      </AuiIf>
      <AuiIf condition={({ threads }) => !threads.isLoading}>
        <ThreadListPrimitive.Items components={{ ThreadListItem }} />
      </AuiIf>
    </ThreadListPrimitive.Root>
  );
};

const ThreadListItem: FC = () => {
  return (
    <ThreadListItemPrimitive.Root className={styles.threadItem}>
      <ThreadListItemPrimitive.Trigger className={styles.threadTrigger}>
        <ThreadListItemPrimitive.Title fallback="New chat" />
      </ThreadListItemPrimitive.Trigger>
    </ThreadListItemPrimitive.Root>
  );
};
