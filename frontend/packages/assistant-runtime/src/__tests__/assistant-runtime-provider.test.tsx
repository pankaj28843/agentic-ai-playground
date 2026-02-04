import type { ReactNode } from "react";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { AssistantRuntimeProvider } from "../index";
import { createChatAdapter } from "../adapters";

vi.mock("@assistant-ui/react", () => {
  return {
    AssistantRuntimeProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
    unstable_useRemoteThreadListRuntime: (options: { runtimeHook: () => unknown }) => {
      options.runtimeHook();
      return {};
    },
    useLocalRuntime: (adapter: unknown) => adapter,
    useAssistantRuntime: () => ({}),
    useThreadList: () => ({
      mainThreadId: null,
      isLoading: false,
      threadIds: [],
      threadItems: {},
    }),
  };
});

vi.mock("../adapters", async () => {
  const actual = await vi.importActual<typeof import("../adapters")>("../adapters");
  return {
    ...actual,
    createChatAdapter: vi.fn(() => ({
      run: async function* () {
        yield {};
      },
    })),
    threadListAdapter: {},
  };
});

describe("AssistantRuntimeProvider", () => {
  beforeAll(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("keeps run mode and overrides getters in sync", async () => {
    const container = document.createElement("div");
    const root = createRoot(container);

    let getRunMode: (() => string | undefined) | undefined;
    let getOverrides: (() => { modelOverride?: string | null } | undefined) | undefined;

    vi.mocked(createChatAdapter).mockImplementation((runModeGetter, overridesGetter) => {
      getRunMode = runModeGetter;
      getOverrides = overridesGetter;
      return {
        run: async function* () {
          yield {};
        },
      };
    });

    await act(async () => {
      root.render(
        <AssistantRuntimeProvider runMode="quick" runOverrides={{ modelOverride: "m1" }}>
          <div />
        </AssistantRuntimeProvider>,
      );
    });

    expect(getRunMode?.()).toBe("quick");
    expect(getOverrides?.()?.modelOverride).toBe("m1");

    await act(async () => {
      root.render(
        <AssistantRuntimeProvider runMode="graph" runOverrides={{ modelOverride: "m2" }}>
          <div />
        </AssistantRuntimeProvider>,
      );
    });

    expect(getRunMode?.()).toBe("graph");
    expect(getOverrides?.()?.modelOverride).toBe("m2");

    await act(async () => {
      root.unmount();
    });
  });
});
