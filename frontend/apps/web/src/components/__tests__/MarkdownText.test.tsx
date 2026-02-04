import { fireEvent, render, screen, cleanup, waitFor } from "@testing-library/react";
import { createElement, type ComponentType } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const markdownMocks = vi.hoisted(() => ({
  useIsMarkdownCodeBlock: vi.fn(() => false),
}));

vi.mock("@assistant-ui/react-markdown", () => ({
  MarkdownTextPrimitive: ({ preprocess }: { preprocess?: (text: string) => string }) => (
    <div data-testid="markdown">{preprocess?.("<thinking>hide</thinking> show")}</div>
  ),
  unstable_memoizeMarkdownComponents: (components: Record<string, unknown>) => components,
  useIsMarkdownCodeBlock: markdownMocks.useIsMarkdownCodeBlock,
}));

vi.mock("react-syntax-highlighter", () => ({
  Prism: ({ children }: { children: string }) => <pre>{children}</pre>,
}));

import {
  MarkdownText,
  markdownComponents,
  stripThinkingTags,
  useCopyToClipboard,
} from "../MarkdownText";

afterEach(() => {
  cleanup();
});

const CopyProbe = ({ value, duration }: { value: string; duration?: number }) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard(duration);
  return (
    <div>
      <button type="button" onClick={() => copyToClipboard(value)}>
        copy
      </button>
      <span data-testid="status">{isCopied ? "yes" : "no"}</span>
    </div>
  );
};

describe("useCopyToClipboard", () => {
  it("uses clipboard API when available", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    render(<CopyProbe value="hello" duration={1} />);

    fireEvent.click(screen.getByText("copy"));

    expect(writeText).toHaveBeenCalledWith("hello");
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("yes");
    });

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("no");
    });
  });

  it("falls back to execCommand when clipboard is unavailable", async () => {
    Object.assign(navigator, { clipboard: undefined });
    const execCommand = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", { value: execCommand, writable: true });

    render(<CopyProbe value="fallback" duration={1} />);

    fireEvent.click(screen.getByText("copy"));

    expect(execCommand).toHaveBeenCalledWith("copy");
    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("yes");
    });

    await waitFor(() => {
      expect(screen.getByTestId("status").textContent).toBe("no");
    });
  });
});

describe("MarkdownText helpers", () => {
  it("strips thinking tags", () => {
    expect(stripThinkingTags("<thinking>secret</thinking> visible")).toBe("visible");
    expect(stripThinkingTags("<thinking>secret")).toBe("secret");
  });

  it("renders default markdown components", async () => {
    const components = markdownComponents;
    const renderComponent = (Component: unknown, props: Record<string, unknown> = {}) => {
      render(createElement(Component as ComponentType<Record<string, unknown>>, props));
    };
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
    render(<MarkdownText />);
    expect(screen.getByTestId("markdown").textContent).toBe("show");

    renderComponent(components.h1, { children: "Title" });
    renderComponent(components.h2, { children: "Title" });
    renderComponent(components.h3, { children: "Title" });
    renderComponent(components.h4, { children: "Title" });
    renderComponent(components.p, { children: "Text" });
    renderComponent(components.a, { href: "/", children: "Link" });
    renderComponent(components.strong, { children: "Strong" });
    renderComponent(components.em, { children: "Em" });
    renderComponent(components.ul, { children: "List" });
    renderComponent(components.ol, { children: "List" });
    renderComponent(components.li, { children: "Item" });
    renderComponent(components.blockquote, { children: "Quote" });
    renderComponent(components.hr);
    renderComponent(components.pre, { children: "Pre" });
    renderComponent(components.code, { children: "Inline" });
    markdownMocks.useIsMarkdownCodeBlock.mockReturnValueOnce(true);
    renderComponent(components.code, { children: "Block" });
    renderComponent(components.CodeHeader, { language: "ts", code: "const a = 1" });
    fireEvent.click(screen.getByTitle(/copy code/i));
    await waitFor(() => {
      expect(screen.getByTitle(/copied/i)).toBeInTheDocument();
    });
    renderComponent(components.SyntaxHighlighter, { language: "ts", code: "line1\nline2" });
    renderComponent(components.SyntaxHighlighter, {
      language: "ts",
      code: "line1\nline2\nline3\nline4",
    });
  });
});
