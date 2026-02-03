import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: ["apps/*", "packages/*"],
    include: [
      "apps/**/src/**/*.{test,spec}.{ts,tsx}",
      "apps/**/tests/**/*.{test,spec}.{ts,tsx}",
      "packages/**/src/**/*.{test,spec}.{ts,tsx}",
    ],
    exclude: [
      "**/node_modules/**",
      "**/dist/**",
      "apps/**/tests/e2e/**",
    ],
    environment: "jsdom",
    setupFiles: ["apps/web/src/test/setup.ts"],
    passWithNoTests: true,
  },
});
