import type { FC } from "react";
import { useMemo } from "react";
import { AlertTriangle, CheckCircle2, SlidersHorizontal } from "lucide-react";

import type { ProfilesResponse } from "@agentic-ai-playground/api-client";
import { useResources } from "../contexts/ResourcesContext";
import { useSettings } from "../contexts/SettingsContext";
import styles from "./SettingsPanel.module.css";

const asLower = (value: string) => value.toLowerCase();

export const SettingsPanel: FC<{ profiles: ProfilesResponse | null; runMode: string }> = ({
  profiles,
  runMode,
}) => {
  const {
    models,
    defaultModel,
    toolGroups,
    profileDefaults,
    inferenceProfiles,
    warnings,
    modelOverride,
    toolGroupsOverride,
    setModelOverride,
    setToolGroupsOverride,
    isLoading,
    error,
  } = useSettings();
  const { resources, enabledSkills, enabledPrompts, setEnabledSkills, setEnabledPrompts } =
    useResources();

  const currentProfile = profiles?.profiles?.find((profile) => profile.id === runMode);
  const currentDefaults = profileDefaults.find((profile) => profile.profileId === runMode);
  const isSingleMode = currentProfile?.entrypointType === "single";
  const toolOverrideEnabled = toolGroupsOverride !== null;

  const modelOptions = useMemo(() => {
    const options = models.slice();
    options.sort((a, b) => a.localeCompare(b));
    return options;
  }, [models]);

  const inferenceProfileOptions = useMemo(() => {
    return (inferenceProfiles ?? [])
      .map((profile) => {
        const value = profile.inferenceProfileArn || profile.inferenceProfileId || "";
        const labelBase = profile.name || profile.inferenceProfileId || profile.inferenceProfileArn || "Inference profile";
        const statusLabel = profile.status ? ` (${profile.status})` : "";
        return value
          ? { value, label: `${labelBase}${statusLabel}` }
          : null;
      })
      .filter((entry): entry is { value: string; label: string } => Boolean(entry));
  }, [inferenceProfiles]);
  const allowedOverrideValues = useMemo(() => {
    return new Set([
      ...modelOptions,
      ...inferenceProfileOptions.map((profile) => profile.value),
    ]);
  }, [modelOptions, inferenceProfileOptions]);
  const isInvalidOverride = Boolean(modelOverride) && !allowedOverrideValues.has(modelOverride as string);

  const activeToolGroups = useMemo(() => {
    if (toolGroupsOverride) {
      return new Set(toolGroupsOverride.map(asLower));
    }
    return new Set((currentDefaults?.toolGroups ?? []).map(asLower));
  }, [currentDefaults, toolGroupsOverride]);

  const handleToolToggle = (name: string) => {
    const next = new Set(activeToolGroups);
    if (next.has(name.toLowerCase())) {
      next.delete(name.toLowerCase());
    } else {
      next.add(name.toLowerCase());
    }
    setToolGroupsOverride(Array.from(next).map((value) => toolGroups.find((g) => g.name.toLowerCase() === value)?.name || value));
  };

  const toggleAllTools = (enabled: boolean) => {
    if (!enabled) {
      setToolGroupsOverride([]);
      return;
    }
    setToolGroupsOverride(toolGroups.map((group) => group.name));
  };

  const toggleAllSkills = (enabled: boolean) => {
    const names = resources?.skills.map((skill) => skill.name) ?? [];
    setEnabledSkills(enabled ? names : []);
  };

  const toggleAllPrompts = (enabled: boolean) => {
    const names = resources?.prompts.map((prompt) => prompt.name) ?? [];
    setEnabledPrompts(enabled ? names : []);
  };

  return (
    <section className={styles.panel}>
      <header className={styles.panelHeader}>
        <SlidersHorizontal aria-hidden="true" />
        <div>
          <p className={styles.panelEyebrow}>Run settings</p>
          <h3 className={styles.panelTitle}>Override controls</h3>
        </div>
      </header>

      {error && <p className={styles.panelHint}>{error}</p>}
      {isLoading && <p className={styles.panelHint}>Loading settings...</p>}
      {!isLoading && warnings.length > 0 && (
        <div className={styles.notice}>
          <AlertTriangle aria-hidden="true" />
          <div>
            {warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        </div>
      )}

      {!isLoading && (
        <div className={styles.section}>
          <label className={styles.field}>
            <span>Model override</span>
            <select
              value={modelOverride && allowedOverrideValues.has(modelOverride) ? modelOverride : ""}
              onChange={(event) => setModelOverride(event.target.value || null)}
            >
              <option value="">Use profile default</option>
              <optgroup label="On-demand models">
                {modelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </optgroup>
              {inferenceProfileOptions.length > 0 && (
                <optgroup label="Inference profiles">
                  {inferenceProfileOptions.map((profile) => (
                    <option key={profile.value} value={profile.value}>
                      {profile.label}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            {defaultModel && (
              <span className={styles.fieldHint}>Default: {defaultModel}</span>
            )}
          </label>
          {isInvalidOverride && (
            <div className={styles.notice}>
              <AlertTriangle aria-hidden="true" />
              <div>
                <p>Selected override is not in the allowed list.</p>
                <button type="button" onClick={() => setModelOverride(null)}>
                  Clear override
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className={styles.section}>
        <label className={styles.toggleRow}>
          <input
            type="checkbox"
            checked={toolOverrideEnabled}
            onChange={(event) => {
              const enabled = event.target.checked;
              if (!enabled) {
                setToolGroupsOverride(null);
              } else if (toolGroupsOverride === null) {
                setToolGroupsOverride(toolGroups.map((group) => group.name));
              }
            }}
          />
          <span>Override tool groups</span>
        </label>
        {!isSingleMode && toolOverrideEnabled && (
          <div className={styles.notice}>
            <AlertTriangle aria-hidden="true" />
            Tool overrides apply across all modes and affect every agent in graph/swarm.
          </div>
        )}
        {toolOverrideEnabled && (
          <div className={styles.toolGroupList}>
            <div className={styles.toolGroupActions}>
              <button type="button" onClick={() => toggleAllTools(true)}>
                Enable all
              </button>
              <button type="button" onClick={() => toggleAllTools(false)}>
                Disable all
              </button>
            </div>
            {toolGroups.map((group) => (
              <label key={group.name} className={styles.toolGroupRow}>
                <input
                  type="checkbox"
                  checked={activeToolGroups.has(group.name.toLowerCase())}
                  onChange={() => handleToolToggle(group.name)}
                />
                <div>
                  <span>{group.name}</span>
                  <span className={styles.toolGroupHint}>{group.description}</span>
                </div>
              </label>
            ))}
          </div>
        )}
        {!toolOverrideEnabled && currentDefaults && (
          <p className={styles.panelHint}>
            Using profile tool groups: {currentDefaults.toolGroups.join(", ") || "none"}.
          </p>
        )}
      </div>

      <div className={styles.section}>
        <h4>Skills</h4>
        <div className={styles.resourceActions}>
          <button type="button" onClick={() => toggleAllSkills(true)}>
            Enable all
          </button>
          <button type="button" onClick={() => toggleAllSkills(false)}>
            Disable all
          </button>
        </div>
        <div className={styles.resourceList}>
          {(resources?.skills ?? []).map((skill) => (
            <label key={skill.name} className={styles.resourceRow}>
              <input
                type="checkbox"
                checked={enabledSkills.map(asLower).includes(skill.name.toLowerCase())}
                onChange={(event) => {
                  if (event.target.checked) {
                    setEnabledSkills([...enabledSkills, skill.name]);
                  } else {
                    setEnabledSkills(enabledSkills.filter((name) => name !== skill.name));
                  }
                }}
              />
              <span>{skill.name}</span>
            </label>
          ))}
        </div>
        {enabledSkills.length === 0 && (
          <div className={styles.notice}>
            <AlertTriangle aria-hidden="true" />
            Skills disabled — /skill commands will be rejected.
          </div>
        )}
      </div>

      <div className={styles.section}>
        <h4>Prompt templates</h4>
        <div className={styles.resourceActions}>
          <button type="button" onClick={() => toggleAllPrompts(true)}>
            Enable all
          </button>
          <button type="button" onClick={() => toggleAllPrompts(false)}>
            Disable all
          </button>
        </div>
        <div className={styles.resourceList}>
          {(resources?.prompts ?? []).map((prompt) => (
            <label key={prompt.name} className={styles.resourceRow}>
              <input
                type="checkbox"
                checked={enabledPrompts.map(asLower).includes(prompt.name.toLowerCase())}
                onChange={(event) => {
                  if (event.target.checked) {
                    setEnabledPrompts([...enabledPrompts, prompt.name]);
                  } else {
                    setEnabledPrompts(enabledPrompts.filter((name) => name !== prompt.name));
                  }
                }}
              />
              <span>{prompt.name}</span>
            </label>
          ))}
        </div>
        {enabledPrompts.length === 0 && (
          <div className={styles.notice}>
            <AlertTriangle aria-hidden="true" />
            Prompts disabled — /prompt commands will be rejected.
          </div>
        )}
      </div>

      <div className={styles.sectionFooter}>
        <CheckCircle2 aria-hidden="true" />
        <span>Overrides apply to new runs only.</span>
      </div>
    </section>
  );
};
