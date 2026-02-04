from agent_toolkit.compaction import CompactionSettings, StreamCompactionPolicy


def test_stream_compaction_policy_disabled_keeps_messages() -> None:
    policy = StreamCompactionPolicy(enabled=False, settings=CompactionSettings())
    messages = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "B"},
    ]
    decision = policy.apply(messages)
    assert decision.kept_messages == messages
    assert decision.dropped_messages == []


def test_stream_compaction_policy_trims_messages() -> None:
    policy = StreamCompactionPolicy(enabled=True, settings=CompactionSettings(keep_recent_tokens=1))
    messages = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "B"},
        {"role": "user", "content": "C"},
    ]
    decision = policy.apply(messages)
    assert decision.kept_messages == [messages[-1]]
    assert decision.dropped_messages == messages[:-1]
