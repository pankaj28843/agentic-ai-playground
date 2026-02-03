import { useAssistantApi, useAssistantState } from "@assistant-ui/react";
import type { FC } from "react";
import { useMemo } from "react";

import { useResources } from "../contexts/ResourcesContext";
import { filterResources, type CommandType } from "../utils/commands";
import styles from "./ThreadView.module.css";

const parseMenuState = (text: string): { type: CommandType; query: string } | null => {
  const trimmed = text.trimStart();
  if (!trimmed.startsWith("/")) {
    return null;
  }
  const match = trimmed.match(/^\/(prompt|skill)(?::|\s+)?(.*)$/i);
  if (!match) {
    return null;
  }
  const type = match[1].toLowerCase() as CommandType;
  const query = match[2]?.trim() ?? "";
  return { type, query };
};

export const SlashCommandMenu: FC = () => {
  const api = useAssistantApi();
  const composerText = useAssistantState(({ composer }) => composer.text);
  const { resources, isLoading, error, enabledPrompts, enabledSkills } = useResources();

  const menuState = useMemo(() => parseMenuState(composerText), [composerText]);
  const items = useMemo(() => {
    if (!menuState) {
      return [];
    }
    const enabled = menuState.type === "prompt" ? enabledPrompts : enabledSkills;
    return filterResources(menuState.type, resources, menuState.query, enabled).slice(0, 6);
  }, [menuState, resources, enabledPrompts, enabledSkills]);

  if (!menuState) {
    return null;
  }

  return (
    <div className={styles.slashMenu} role="listbox">
      <div className={styles.slashMenuHeader}>
        {menuState.type === "prompt" ? "Prompt templates" : "Skills"}
      </div>
      {isLoading && <div className={styles.slashMenuHint}>Loading resources...</div>}
      {error && <div className={styles.slashMenuHint}>{error}</div>}
      {!isLoading && !error && items.length === 0 && (
        <div className={styles.slashMenuHint}>No matches</div>
      )}
      {items.map((item) => (
        <button
          key={`${menuState.type}-${item.name}`}
          type="button"
          className={styles.slashMenuItem}
          onClick={() => {
            if (menuState.type === "skill") {
              api.composer().setText(`Skill: ${item.name}\n\n${item.content}`.trim());
            } else {
              api.composer().setText(item.content.trim());
            }
          }}
        >
          <span className={styles.slashMenuName}>{item.name}</span>
          <span className={styles.slashMenuDescription}>{item.description}</span>
        </button>
      ))}
    </div>
  );
};
