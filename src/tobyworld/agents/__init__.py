"""
tobyworld.agents
================

This package contains the Tobyworld Mirror V3 agent layer.

- agent_switcher.py : routes SymbolRouter decisions to specific agents
- (future) gentle_guide.py, oracle_philosopher.py, mechanics_scholar.py, ops_engineer.py

Convenience imports are provided so you can do:

    from tobyworld.agents import AgentSwitcher, default_switcher_for_dev
"""

from .agent_switcher import AgentSwitcher, default_switcher_for_dev

__all__ = [
    "AgentSwitcher",
    "default_switcher_for_dev",
]
