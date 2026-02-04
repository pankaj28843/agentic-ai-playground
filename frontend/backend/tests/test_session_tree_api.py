from __future__ import annotations


def _message(message_id: str, role: str, text: str) -> dict[str, object]:
    return {
        "id": message_id,
        "role": role,
        "content": [{"type": "text", "text": text}],
        "createdAt": "2024-01-15T00:00:00Z",
    }


def test_session_tree_branches_and_labels(client) -> None:
    remote_id = client.post("/api/threads", json={}).json()["remoteId"]

    user1 = _message("u1", "user", "Hello")
    assistant1 = _message("a1", "assistant", "Hi")
    user2 = _message("u2", "user", "Branch")

    assert (
        client.post(f"/api/threads/{remote_id}/messages", json={"message": user1}).status_code
        == 200
    )
    assert (
        client.post(f"/api/threads/{remote_id}/messages", json={"message": assistant1}).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/threads/{remote_id}/messages",
            json={"message": user2, "parentSessionEntryId": "u1"},
        ).status_code
        == 200
    )

    tree = client.get(f"/api/threads/{remote_id}/session-tree").json()
    entries = {entry["id"]: entry for entry in tree["entries"]}
    assert set(entries.keys()) == {"u1", "a1", "u2"}

    children = tree["children"]
    assert set(children["u1"]) == {"a1", "u2"}
    assert tree["roots"] == ["u1"]

    label = client.post(
        f"/api/threads/{remote_id}/session-tree/label",
        json={"entryId": "u1", "label": "Root"},
    ).json()
    assert label["status"] == "ok"

    tree_after = client.get(f"/api/threads/{remote_id}/session-tree").json()
    labeled = {entry["id"]: entry for entry in tree_after["entries"]}
    assert labeled["u1"]["label"] == "Root"
