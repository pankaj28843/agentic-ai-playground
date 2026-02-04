import { assign, setup } from "xstate";

type Theme = "light" | "dark" | "system";

type SystemTheme = "light" | "dark";

type ThemeContext = {
  theme: Theme;
  systemTheme: SystemTheme;
};

type ThemeInput = {
  theme: Theme;
  systemTheme: SystemTheme;
};

type ThemeEvent =
  | { type: "THEME.SET"; value: Theme }
  | { type: "THEME.CYCLE" }
  | { type: "SYSTEM.THEME.CHANGED"; value: SystemTheme };

export const themeMachine = setup({
  types: {
    context: {} as ThemeContext,
    input: {} as ThemeInput,
    events: {} as ThemeEvent,
  },
  actions: {
    assignTheme: assign(({ event }) => {
      return { theme: (event as { value: Theme }).value };
    }),
    cycleTheme: assign(({ context }) => {
      if (context.theme === "system") {
        return { theme: "light" };
      }
      if (context.theme === "light") {
        return { theme: "dark" };
      }
      return { theme: "system" };
    }),
    assignSystemTheme: assign(({ event }) => {
      return { systemTheme: (event as { value: SystemTheme }).value };
    }),
  },
}).createMachine({
  id: "theme",
  context: ({ input }) => ({
    theme: input.theme,
    systemTheme: input.systemTheme,
  }),
  on: {
    "THEME.SET": { actions: "assignTheme" },
    "THEME.CYCLE": { actions: "cycleTheme" },
    "SYSTEM.THEME.CHANGED": { actions: "assignSystemTheme" },
  },
});

export type { Theme, ThemeContext, ThemeEvent, ThemeInput, SystemTheme };
