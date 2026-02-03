import type { PromptResource, ResourcesResponse, SkillResource } from "@agentic-ai-playground/api-client";

export type CommandType = "prompt" | "skill";

export type ResolvedCommand = {
  type: CommandType;
  name: string;
  content: string;
};

const commandPattern = /^\s*\/(prompt|skill)(?::|\s+)(.+)$/i;

export const parseCommand = (text: string): { type: CommandType; query: string } | null => {
  const match = text.match(commandPattern);
  if (!match) {
    return null;
  }
  const type = match[1].toLowerCase() as CommandType;
  const query = match[2].trim();
  if (!query) {
    return null;
  }
  return { type, query };
};

export const resolveCommand = (
  text: string,
  resources: ResourcesResponse | null,
  enabledNames?: string[],
): { resolvedText: string; applied: boolean; error?: string } => {
  const parsed = parseCommand(text);
  if (!parsed || !resources) {
    return { resolvedText: text, applied: false };
  }

  const pool = parsed.type === "prompt" ? resources.prompts : resources.skills;
  const enabled = enabledNames ? new Set(enabledNames.map((name) => name.toLowerCase())) : null;
  const filteredPool = enabled
    ? pool.filter((item) => enabled.has(item.name.toLowerCase()))
    : pool;
  const match = findResource(filteredPool, parsed.query);
  if (!match) {
    return { resolvedText: text, applied: false, error: `Unknown ${parsed.type}: ${parsed.query}` };
  }

  const resolvedText = formatResolvedText(parsed.type, match.name, match.content);
  if (!resolvedText) {
    return {
      resolvedText: text,
      applied: false,
      error: `${parsed.type === "prompt" ? "Prompt" : "Skill"} "${match.name}" is empty.`,
    };
  }
  return { resolvedText, applied: true };
};

export const filterResources = (
  type: CommandType,
  resources: ResourcesResponse | null,
  query: string,
  enabledNames?: string[],
): Array<PromptResource | SkillResource> => {
  if (!resources) {
    return [];
  }
  const pool = type === "prompt" ? resources.prompts : resources.skills;
  const enabled = enabledNames ? new Set(enabledNames.map((name) => name.toLowerCase())) : null;
  const filteredPool = enabled
    ? pool.filter((item) => enabled.has(item.name.toLowerCase()))
    : pool;
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return filteredPool;
  }
  return filteredPool.filter((item) =>
    `${item.name} ${item.description}`.toLowerCase().includes(needle),
  );
};

const findResource = (
  pool: Array<PromptResource | SkillResource>,
  query: string,
): PromptResource | SkillResource | null => {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return null;
  }
  return pool.find((item) => item.name.toLowerCase() === needle) ?? null;
};

const formatResolvedText = (type: CommandType, name: string, content: string): string => {
  if (type === "skill") {
    return `Skill: ${name}\n\n${content}`.trim();
  }
  return content.trim();
};
