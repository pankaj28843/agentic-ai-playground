"use client";

import {
  MarkdownTextPrimitive,
  unstable_memoizeMarkdownComponents as memoizeMarkdownComponents,
  useIsMarkdownCodeBlock,
  type CodeHeaderProps,
} from "@assistant-ui/react-markdown";
import remarkGfm from "remark-gfm";
import { type FC, memo } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Check, Copy } from "lucide-react";
import { useMachine } from "@xstate/react";
import { setup } from "xstate";

import styles from "./MarkdownText.module.css";

const cx = (...classes: Array<string | false | null | undefined>) => classes.filter(Boolean).join(" ");

/**
 * Strip <thinking>...</thinking> tags from text.
 * These are shown in the trace panel instead.
 * Also handles malformed/partial thinking tags from streaming artifacts.
 */
export const stripThinkingTags = (text: string): string => {
  // First, strip complete thinking blocks
  let result = text.replace(/<thinking>[\s\S]*?<\/thinking>\s*/g, "");
  // Then strip any orphaned/malformed opening tags (including partial ones)
  result = result.replace(/<thinking[^>]*>/g, "");
  // Strip any orphaned closing tags
  result = result.replace(/<\/thinking>/g, "");
  return result.trim();
};

/**
 * Hook for copy-to-clipboard with visual feedback
 */
type CopyContext = {
  copiedDuration: number;
};

type CopyInput = {
  copiedDuration: number;
};

type CopyEvent = { type: "COPY.SUCCESS" };

const copyMachine = setup({
  types: {
    context: {} as CopyContext,
    input: {} as CopyInput,
    events: {} as CopyEvent,
  },
  delays: {
    COPY_RESET: ({ context }) => context.copiedDuration,
  },
}).createMachine({
  id: "copy",
  context: ({ input }) => ({
    copiedDuration: input.copiedDuration,
  }),
  initial: "idle",
  states: {
    idle: {
      on: {
        "COPY.SUCCESS": { target: "copied" },
      },
    },
    copied: {
      after: {
        COPY_RESET: { target: "idle" },
      },
    },
  },
});

export const useCopyToClipboard = (copiedDuration = 2000) => {
  const [state, send] = useMachine(copyMachine, {
    input: { copiedDuration },
  });
  const isCopied = state.matches("copied");

  const copyToClipboard = (value: string) => {
    if (!value) return;

    // Use clipboard API if available (secure context)
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(value).then(() => send({ type: "COPY.SUCCESS" }));
    } else {
      // Fallback for non-secure contexts
      const textarea = document.createElement("textarea");
      textarea.value = value;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand("copy");
        send({ type: "COPY.SUCCESS" });
      } finally {
        document.body.removeChild(textarea);
      }
    }
  };

  return { isCopied, copyToClipboard };
};

/**
 * Code block header with language label and copy button
 */
const CodeHeader: FC<CodeHeaderProps> = ({ language, code }) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard();

  const onCopy = () => {
    if (!code || isCopied) return;
    copyToClipboard(code);
  };

  return (
    <div className={styles.codeHeader}>
      <span className={styles.codeLanguage}>{language || "text"}</span>
      <button
        type="button"
        className={styles.codeCopyBtn}
        onClick={onCopy}
        title={isCopied ? "Copied!" : "Copy code"}
      >
        {isCopied ? <Check size={14} /> : <Copy size={14} />}
      </button>
    </div>
  );
};

/**
 * Syntax highlighter component using Prism
 */
const CodeBlockHighlighter: FC<{
  language: string;
  code: string;
}> = ({ language, code }) => {
  return (
    <SyntaxHighlighter
      language={language || "text"}
      style={oneDark}
      customStyle={{
        margin: 0,
        borderRadius: "0 0 8px 8px",
        fontSize: "0.875rem",
      }}
      showLineNumbers={code.split("\n").length > 3}
      wrapLines
    >
      {code}
    </SyntaxHighlighter>
  );
};

/**
 * Memoized markdown components with syntax highlighting
 */
const defaultComponents = memoizeMarkdownComponents({
  // Headings
  h1: ({ className, ...props }) => <h1 className={className} {...props} />,
  h2: ({ className, ...props }) => <h2 className={className} {...props} />,
  h3: ({ className, ...props }) => <h3 className={className} {...props} />,
  h4: ({ className, ...props }) => <h4 className={className} {...props} />,

  // Text elements
  p: ({ className, ...props }) => <p className={className} {...props} />,
  a: ({ className, ...props }) => (
    <a
      className={className}
      target="_blank"
      rel="noopener noreferrer"
      {...props}
    />
  ),
  strong: ({ className, ...props }) => <strong className={className} {...props} />,
  em: ({ className, ...props }) => <em className={className} {...props} />,

  // Lists
  ul: ({ className, ...props }) => <ul className={className} {...props} />,
  ol: ({ className, ...props }) => <ol className={className} {...props} />,
  li: ({ className, ...props }) => <li className={className} {...props} />,

  // Other elements
  blockquote: ({ className, ...props }) => <blockquote className={className} {...props} />,
  hr: ({ className, ...props }) => <hr className={className} {...props} />,

  // Code elements
  pre: ({ className, ...props }) => (
    <pre className={cx(styles.markdownPre, className)} {...props} />
  ),
  code: function Code({ className, ...props }) {
    const isCodeBlock = useIsMarkdownCodeBlock();
    const codeClass = isCodeBlock ? styles.markdownCodeBlock : styles.markdownInlineCode;
    return (
      <code
        className={cx(codeClass, className)}
        {...props}
      />
    );
  },

  // Code header with copy button
  CodeHeader,

  // Syntax highlighter for code blocks
  SyntaxHighlighter: ({ language, code }: { language: string; code: string }) => (
    <CodeBlockHighlighter language={language} code={code} />
  ),
});

/**
 * Custom text component that strips thinking tags before rendering.
 * Uses the built-in preprocess prop from MarkdownTextPrimitive.
 */
const MarkdownTextImpl = () => {
  return (
    <MarkdownTextPrimitive
      className={styles.markdown}
      remarkPlugins={[remarkGfm]}
      preprocess={stripThinkingTags}
      components={defaultComponents}
    />
  );
};

export const MarkdownText = memo(MarkdownTextImpl);

export const markdownComponents = defaultComponents;
