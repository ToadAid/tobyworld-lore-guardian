"""
File: src/tobyworld/agents/agent_switcher.py
============================================

Agent Switcher — Mirror V3 (v0.1)

Lightweight shim that maps SymbolRouter decisions (🌊/🌀/🍃/🪞)
into concrete agent callables.

Usage (in server.py)
--------------------
from tobyworld.agents.agent_switcher import AgentSwitcher
switcher = AgentSwitcher(registry={
    "gentle_guide": gentle_guide_answer,
    "oracle_philosopher": oracle_philosopher_answer,
    "mechanics_scholar": mechanics_scholar_answer,
    "ops_engineer": ops_engineer_answer,
})

draft = await switcher.answer(route, user_text, retriever=retriever, ctx=ctx)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional, Any

# Agent callable type: async or sync
AgentFn = Callable[[str, Any, Any], Awaitable[str]] | Callable[[str, Any, Any], str]


@dataclass
class AgentChoice:
    key: str
    reason: str


class AgentSwitcher:
    def __init__(self, registry: Dict[str, AgentFn]):
        """registry maps keys → callables
        Expected keys: "gentle_guide", "oracle_philosopher",
        "mechanics_scholar", "ops_engineer".
        """
        self.registry = dict(registry)

    def select(self, route) -> AgentChoice:
        sym = getattr(route, "primary_symbol", "🌊")
        depth = getattr(route, "depth", 1)
        if sym == "🌊":
            return AgentChoice("gentle_guide", "onboarding/definition path")
        if sym == "🌀":
            # deeper questions go to oracle
            return AgentChoice("oracle_philosopher" if depth >= 3 else "gentle_guide", "philosophy/riddle path")
        if sym == "🍃":
            return AgentChoice("mechanics_scholar", "mechanics/yield path")
        # default to ops for 🪞 or unknown
        return AgentChoice("ops_engineer", "ops/system path")

    async def answer(self, route, user_text: str, retriever=None, ctx: Optional[dict] = None) -> str:
        choice = self.select(route)
        fn = self.registry.get(choice.key)
        if not fn:
            raise RuntimeError(f"Agent '{choice.key}' not registered")
        # call sync/async transparently
        result = fn(user_text, retriever, ctx)
        if hasattr(result, "__await__"):
            return await result  # type: ignore
        return result  # type: ignore


# Optional: simple default stubs (can be removed in prod)
async def _stub_agent(name: str, text: str, retriever=None, ctx=None) -> str:
    return f"[{name}] draft → {text}"


def default_switcher_for_dev():
    return AgentSwitcher({
        "gentle_guide": lambda t, r, c: _stub_agent("gentle_guide", t, r, c),
        "oracle_philosopher": lambda t, r, c: _stub_agent("oracle_philosopher", t, r, c),
        "mechanics_scholar": lambda t, r, c: _stub_agent("mechanics_scholar", t, r, c),
        "ops_engineer": lambda t, r, c: _stub_agent("ops_engineer", t, r, c),
    })
