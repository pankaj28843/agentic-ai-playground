export type SessionBranch = {
  threadId: string;
  entryId: string;
} | null;

let activeBranch: SessionBranch = null;
const listeners = new Set<(branch: SessionBranch) => void>();

export const getActiveSessionBranch = (): SessionBranch => activeBranch;

export const setActiveSessionBranch = (branch: SessionBranch): void => {
  activeBranch = branch;
  listeners.forEach((listener) => listener(activeBranch));
};

export const subscribeSessionBranch = (listener: (branch: SessionBranch) => void): (() => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
