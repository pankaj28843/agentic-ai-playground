import { defineProject } from "vitest/config";

export default defineProject({
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      all: true,
      include: [
        "src/App.tsx",
        "src/components/MarkdownText.tsx",
        "src/components/QueuedComposerControls.tsx",
        "src/components/SessionTreePanel.tsx",
        "src/components/SettingsPanel.tsx",
        "src/components/TracePanel.tsx",
        "src/contexts/**/*.{ts,tsx}",
        "src/hooks/**/*.{ts,tsx}",
        "src/state/**/*.{ts,tsx}",
      ],
      exclude: ["src/test/**", "src/**/__tests__/**", "src/**/tests/**", "src/**/*.d.ts"],
      thresholds: {
        statements: 100,
        branches: 100,
        functions: 100,
        lines: 100,
      },
    },
  },
});
