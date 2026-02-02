from agent_toolkit.session_browser import list_sessions


def test_list_sessions(tmp_path) -> None:
    (tmp_path / "session_alpha").mkdir()
    (tmp_path / "session_beta").mkdir()
    (tmp_path / "notes").mkdir()
    sessions = list_sessions(str(tmp_path))
    assert sessions == ["alpha", "beta"]
