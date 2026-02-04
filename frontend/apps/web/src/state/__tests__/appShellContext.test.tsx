import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShellProvider, useAppShell } from "../appShellContext";

const AppShellProbe = () => {
  const {
    menuOpen,
    shouldCloseTrace,
    toggleMenu,
    openMenu,
    closeMenu,
    setConversationId,
    acknowledgeTraceClosed,
  } = useAppShell();

  return (
    <div>
      <div data-testid="menu">{menuOpen ? "open" : "closed"}</div>
      <div data-testid="trace">{shouldCloseTrace ? "yes" : "no"}</div>
      <button type="button" onClick={toggleMenu}>
        toggle
      </button>
      <button type="button" onClick={openMenu}>
        open
      </button>
      <button type="button" onClick={closeMenu}>
        close
      </button>
      <button type="button" onClick={() => setConversationId("thread-1")}>set-1</button>
      <button type="button" onClick={() => setConversationId("thread-2")}>set-2</button>
      <button type="button" onClick={acknowledgeTraceClosed}>ack</button>
    </div>
  );
};

describe("AppShellProvider", () => {
  it("updates menu and trace flags", async () => {
    render(
      <AppShellProvider>
        <AppShellProbe />
      </AppShellProvider>,
    );

    expect(screen.getByTestId("menu").textContent).toBe("closed");
    screen.getByText("toggle").click();
    await waitFor(() => {
      expect(screen.getByTestId("menu").textContent).toBe("open");
    });
    screen.getByText("close").click();
    await waitFor(() => {
      expect(screen.getByTestId("menu").textContent).toBe("closed");
    });
    screen.getByText("open").click();
    await waitFor(() => {
      expect(screen.getByTestId("menu").textContent).toBe("open");
    });

    screen.getByText("set-1").click();
    await waitFor(() => {
      expect(screen.getByTestId("trace").textContent).toBe("no");
    });
    screen.getByText("set-2").click();
    await waitFor(() => {
      expect(screen.getByTestId("trace").textContent).toBe("yes");
    });

    screen.getByText("ack").click();
    await waitFor(() => {
      expect(screen.getByTestId("trace").textContent).toBe("no");
    });
  });
});
