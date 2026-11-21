"""Technology adapter registry (subphase 3.5).

A technology adapter provides deterministic build, test, and lint commands for
a project's stack (README §7.2, FR-2.2). Detection is rule-based over the
repository's manifest files; commands are then executed inside the workspace by
the terminal/test runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Adapter:
    """A versioned technology adapter with command templates."""

    name: str
    version: str
    build: list[str] = field(default_factory=list)
    test: list[str] = field(default_factory=list)
    lint: list[str] = field(default_factory=list)
    install: list[str] = field(default_factory=list)
    image: str = "python:3.12-slim"
    markers: tuple[str, ...] = ()


ADAPTERS: tuple[Adapter, ...] = (
    Adapter(
        name="python",
        version="1",
        build=["python -m pip install -e ."],
        test=["python -m pytest"],
        lint=["ruff check ."],
        install=["python -m pip install -e .[dev]"],
        image="python:3.12-slim",
        markers=("pyproject.toml", "setup.py", "requirements.txt", "Pipfile"),
    ),
    Adapter(
        name="nextjs",
        version="1",
        build=["pnpm build"],
        test=["pnpm test"],
        lint=["pnpm lint"],
        install=["pnpm install"],
        image="node:20-slim",
        markers=("package.json", "pnpm-lock.yaml", "next.config.js"),
    ),
    Adapter(
        name="spring-boot",
        version="1",
        build=["./mvnw -q compile"],
        test=["./mvnw -q test"],
        lint=["./mvnw -q verify"],
        install=["./mvnw -q dependency:resolve"],
        image="eclipse-temurin:21-jdk",
        markers=("pom.xml", "build.gradle"),
    ),
    Adapter(
        name="laravel",
        version="1",
        build=["composer install --no-interaction"],
        test=["php artisan test"],
        lint=["php artisan pint --test"],
        install=["composer install --no-interaction"],
        image="php:8.3-cli",
        markers=("composer.json", "artisan"),
    ),
)


def detect(repository_files: list[str]) -> Adapter:
    """Pick the first adapter whose markers are present in the repo."""
    for adapter in ADAPTERS:
        if any(marker in repository_files for marker in adapter.markers):
            return adapter
    return ADAPTERS[0]  # default to python when unknown


def get_adapter(name: str) -> Adapter:
    """Return an adapter by name, falling back to the default."""
    for adapter in ADAPTERS:
        if adapter.name == name:
            return adapter
    return ADAPTERS[0]