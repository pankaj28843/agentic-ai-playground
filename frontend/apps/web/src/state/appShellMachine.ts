import { assign, setup } from "xstate";

type AppShellContext = {
  menuOpen: boolean;
  conversationId: string | null;
  hasInitialized: boolean;
  shouldCloseTrace: boolean;
};

type AppShellInput = {
  menuOpen?: boolean;
  conversationId?: string | null;
};

type AppShellEvent =
  | { type: "MENU.TOGGLE" }
  | { type: "MENU.OPEN" }
  | { type: "MENU.CLOSE" }
  | { type: "ROUTE.CONVERSATION.SET"; value: string | null }
  | { type: "TRACE.CLOSE.ACK" };

export const appShellMachine = setup({
  types: {
    context: {} as AppShellContext,
    input: {} as AppShellInput,
    events: {} as AppShellEvent,
  },
  actions: {
    toggleMenu: assign(({ context }) => ({ menuOpen: !context.menuOpen })),
    openMenu: assign({ menuOpen: true }),
    closeMenu: assign({ menuOpen: false }),
    assignConversation: assign(({ context, event }) => {
      const nextConversationId = (event as { value: string | null }).value;
      const hasChanged = context.conversationId !== nextConversationId;
      const shouldCloseTrace = context.hasInitialized && hasChanged;
      return {
        conversationId: nextConversationId,
        hasInitialized: true,
        shouldCloseTrace: context.shouldCloseTrace || shouldCloseTrace,
        menuOpen: shouldCloseTrace ? false : context.menuOpen,
      };
    }),
    acknowledgeTraceClose: assign({ shouldCloseTrace: false }),
  },
}).createMachine({
  id: "appShell",
  context: ({ input }) => ({
    menuOpen: input?.menuOpen ?? false,
    conversationId: input?.conversationId ?? null,
    hasInitialized: false,
    shouldCloseTrace: false,
  }),
  on: {
    "MENU.TOGGLE": { actions: "toggleMenu" },
    "MENU.OPEN": { actions: "openMenu" },
    "MENU.CLOSE": { actions: "closeMenu" },
    "ROUTE.CONVERSATION.SET": { actions: "assignConversation" },
    "TRACE.CLOSE.ACK": { actions: "acknowledgeTraceClose" },
  },
});

export type { AppShellContext, AppShellEvent, AppShellInput };
