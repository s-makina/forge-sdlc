"""Lightweight dependency-injection container.

Holds application-wide singletons keyed by name. This is deliberately minimal:
FastAPI's ``Depends`` handles per-request wiring; this container is for the few
process-wide objects that are awkward to construct inline (e.g. the settings
snapshot and the model gateway client added in Phase 2).
"""

from __future__ import annotations

from typing import Any, cast

from app.core.config import Settings, get_settings


class Container:
    """A tiny service registry."""

    def __init__(self) -> None:
        self._singletons: dict[str, Any] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._singletons["settings"] = get_settings()

    def register(self, name: str, instance: Any) -> None:
        self._singletons[name] = instance

    def unregister(self, name: str) -> None:
        """Drop a service so a later ``resolve`` raises ``KeyError`` again."""
        self._singletons.pop(name, None)

    def resolve(self, name: str) -> Any:
        if name not in self._singletons:
            raise KeyError(f"No service registered under '{name}'")
        return self._singletons[name]

    @property
    def settings(self) -> Settings:
        return cast(Settings, self.resolve("settings"))


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container
