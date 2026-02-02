import { AlertCircle, Home } from "lucide-react";
import type { FC } from "react";
import styles from "./ThreadNotFound.module.css";

interface ThreadNotFoundProps {
  onGoHome: () => void;
}

export const ThreadNotFound: FC<ThreadNotFoundProps> = ({ onGoHome }) => {
  return (
    <div className={styles.threadNotFound}>
      <div className={styles.threadNotFoundIcon}>
        <AlertCircle aria-hidden="true" />
      </div>
      <h2 className={styles.threadNotFoundTitle}>Thread not found</h2>
      <p className={styles.threadNotFoundText}>
        The conversation you are looking for does not exist or may have been deleted.
      </p>
      <button type="button" className={styles.threadNotFoundButton} onClick={onGoHome}>
        <Home aria-hidden="true" />
        <span>Go to home</span>
      </button>
    </div>
  );
};
