import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useTheme } from "../../hooks";
import { ThemeProvider } from "../themeContext";

type Listener = () => void;

const setupMatchMedia = (initialMatches: boolean) => {
  let matches = initialMatches;
  const listeners = new Set<Listener>();

  const mediaQuery = {
    get matches() {
      return matches;
    },
    addEventListener: (_event: string, listener: Listener) => {
      listeners.add(listener);
    },
    removeEventListener: (_event: string, listener: Listener) => {
      listeners.delete(listener);
    },
  };

  const matchMedia = vi.fn().mockImplementation(() => mediaQuery);

  Object.defineProperty(window, "matchMedia", {
    value: matchMedia,
    writable: true,
  });

  return {
    setMatches: (next: boolean) => {
      matches = next;
      listeners.forEach((listener) => listener());
    },
  };
};

const ThemeProbe = () => {
  const { theme, resolvedTheme, cycleTheme } = useTheme();
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <div data-testid="resolved">{resolvedTheme}</div>
      <button type="button" onClick={cycleTheme}>
        cycle
      </button>
    </div>
  );
};

describe("ThemeProvider", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    cleanup();
  });
  it("applies stored theme and updates document attribute", () => {
    localStorage.setItem("theme-preference", "dark");
    setupMatchMedia(false);

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByTestId("theme").textContent).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("cycles theme and persists", async () => {
    localStorage.setItem("theme-preference", "system");
    setupMatchMedia(false);

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    screen.getAllByText("cycle")[0].click();
    await waitFor(() => {
      expect(screen.getByTestId("theme").textContent).toBe("light");
    });
    expect(localStorage.getItem("theme-preference")).toBe("light");
  });

  it("updates resolved theme on system changes", async () => {
    localStorage.setItem("theme-preference", "system");
    const media = setupMatchMedia(false);

    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getAllByTestId("resolved")[0].textContent).toBe("light");
    media.setMatches(true);
    await waitFor(() => {
      expect(screen.getAllByTestId("resolved")[0].textContent).toBe("dark");
    });
  });
});
