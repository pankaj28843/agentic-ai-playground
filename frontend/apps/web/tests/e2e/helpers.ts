import type { Page } from "@playwright/test";
import { expect } from "@playwright/test";

export const waitForAssistantDone = async (page: Page, timeout = 30000) => {
  const assistantMessages = page.locator('[data-role="assistant"]');
  const lastAssistant = assistantMessages.last();
  await expect(
    lastAssistant.getByTestId("message-status-assistant").getByText("done", { exact: true })
  ).toBeVisible({ timeout });
};
