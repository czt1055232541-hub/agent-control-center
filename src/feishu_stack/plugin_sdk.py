"""Public contracts for Agent Control Center feature plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncContextManager, Callable, Literal

from fastapi import APIRouter, FastAPI


PluginKind = Literal["framework", "feature", "integration"]
PluginState = Literal["native", "transitional"]
RouterFactory = Callable[[], APIRouter]
LifespanFactory = Callable[[FastAPI], AsyncContextManager[None]]


@dataclass(frozen=True, slots=True)
class PluginCard:
    """A host-neutral UI contribution advertised by an ACC plugin."""

    id: str
    title: str
    description: str
    page: str
    icon: str = "package"
    order: int = 100


@dataclass(frozen=True, slots=True)
class AccPlugin:
    """One independently installable contribution to the ACC framework.

    ``router_factory`` is intentionally lazy: importing a plugin may describe it,
    but routers and their runtime dependencies are created only when ACC mounts
    the resolved plugin graph.
    """

    id: str
    name: str
    version: str
    description: str
    kind: PluginKind = "feature"
    state: PluginState = "native"
    requires: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    cards: tuple[PluginCard, ...] = ()
    router_factory: RouterFactory | None = field(default=None, repr=False, compare=False)
    lifespan: LifespanFactory | None = field(default=None, repr=False, compare=False)
