"""Extension runtime models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class ExtensionCommand:
    """Command registered by an extension."""

    name: str
    description: str
    handler: Callable[[str], Any]


@dataclass(frozen=True)
class ExtensionError:
    """Captured extension execution error."""

    extension_name: str
    event_name: str
    message: str
