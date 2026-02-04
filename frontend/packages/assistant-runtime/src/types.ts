export type RunOverrides = {
  modelOverride?: string | null;
  toolGroupsOverride?: string[] | null;
};

export type PhoenixMetadata = {
  traceId?: string;
  sessionId?: string;
};

export type RuntimeMetadata = {
  runMode?: string;
  profileName?: string;
  modelId?: string;
  executionMode?: string;
  entrypointReference?: string;
};
