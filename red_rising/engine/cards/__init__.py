"""Card deploy abilities.

Importing this package runs every tier module, which registers each card's deploy
script into `abilities.REGISTRY` via the `@deploy` decorator. `rules.py` imports the
package so the registry is populated before any game runs.
"""

from __future__ import annotations

from . import tier0, tier1, tier2, tier3  # noqa: F401  (import = @deploy registration)

__all__ = ["tier0", "tier1", "tier2", "tier3"]
