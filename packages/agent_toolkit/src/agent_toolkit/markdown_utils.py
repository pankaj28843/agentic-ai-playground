"""Markdown frontmatter helpers."""

from __future__ import annotations


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML-style frontmatter from a markdown string."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            frontmatter_lines = lines[1:idx]
            body = "\n".join(lines[idx + 1 :])
            meta: dict[str, str] = {}
            for line in frontmatter_lines:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip().strip('"')
            return meta, body
    return {}, text


def first_non_empty_line(text: str) -> str:
    """Return the first non-empty line of a text block."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""
