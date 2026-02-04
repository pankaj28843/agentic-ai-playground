import type { ReactNode } from "react";
import { useEffect } from "react";

/* eslint-disable react-refresh/only-export-components */
import { createActorContext } from "@xstate/react";
import type { SnapshotFrom } from "xstate";

import { themeMachine, type Theme, type SystemTheme } from "./themeMachine";

const STORAGE_KEY = "theme-preference";

const getStoredTheme = (): Theme => {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
};

const getSystemTheme = (): SystemTheme => {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

const applyTheme = (theme: Theme) => {
  const root = document.documentElement;
  if (theme === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", theme);
  }
};

const ThemeActorContext = createActorContext(themeMachine);

export type ThemeSnapshot = SnapshotFrom<typeof themeMachine>;

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const initialTheme = getStoredTheme();
  const initialSystemTheme = getSystemTheme();

  return (
    <ThemeActorContext.Provider
      logic={themeMachine}
      options={{ input: { theme: initialTheme, systemTheme: initialSystemTheme } }}
    >
      <ThemeEffects />
      {children}
    </ThemeActorContext.Provider>
  );
};

const ThemeEffects = () => {
  const actorRef = ThemeActorContext.useActorRef();
  const theme = ThemeActorContext.useSelector((state) => state.context.theme);

  useEffect(() => {
    applyTheme(theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Ignore storage errors
    }
  }, [theme]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      actorRef.send({
        type: "SYSTEM.THEME.CHANGED",
        value: mediaQuery.matches ? "dark" : "light",
      });
    };
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, [actorRef]);

  return null;
};

export const useTheme = () => {
  const actorRef = ThemeActorContext.useActorRef();
  const theme = ThemeActorContext.useSelector((state) => state.context.theme);
  const systemTheme = ThemeActorContext.useSelector((state) => state.context.systemTheme);

  const resolvedTheme = theme === "system" ? systemTheme : theme;

  const setTheme = (value: Theme) => {
    actorRef.send({ type: "THEME.SET", value });
  };

  const cycleTheme = () => {
    actorRef.send({ type: "THEME.CYCLE" });
  };

  return { theme, systemTheme, resolvedTheme, setTheme, cycleTheme };
};
