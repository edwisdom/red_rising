"""Turn the parquet's markdown card text into structured data.

Used at build time by `build_cards.py`, and directly by tests. Kept separate from
the builder so the tricky bits (anchor resolution, clause splitting) are testable
without touching pandas.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from red_rising.carddefs import Ability, BonusClause, Ref, RefKind
from red_rising.enums import COLOR_BY_PLURAL, Color

#: `[Golds](#golds)` -> (label, anchor)
LINK_RE = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")

#: Glossary anchors that point at rules terms rather than game objects.
KEYWORD_ANCHORS = frozenset({"banish", "block", "deploy", "reveal", "lead", "scout"})

#: Card text uses a Unicode minus (U+2212) for negative point values.
MINUS = "−"

#: `15: if with Octavia.` / `−10: if with Victra.` / `?: Gain the core value...`
CLAUSE_RE = re.compile(rf"^\s*(?P<pts>[{MINUS}\-]?\d+|\?)\s*:\s*(?P<cond>.+?)\s*$", re.DOTALL)


class UnresolvedAnchor(ValueError):
    """An anchor in card text that maps to no color, card, or keyword."""


def strip_links(md: str) -> str:
    """Flatten `[label](#anchor)` to `label`, leaving readable prose."""
    return LINK_RE.sub(r"\1", md).strip()


def make_resolver(card_ids: Iterable[str]) -> AnchorResolver:
    return AnchorResolver(frozenset(card_ids))


class AnchorResolver:
    """Maps a markdown anchor to a canonical (kind, target) pair.

    Anchors are slugified card *names*, so "The Jackal" yields `#the-jackal`
    while the card id is `jackal`. Colors appear in their plural form.
    """

    def __init__(self, card_ids: frozenset[str]) -> None:
        self._card_ids = card_ids

    def resolve(self, anchor: str) -> tuple[RefKind, str]:
        a = anchor.strip().lower()

        if a in KEYWORD_ANCHORS:
            return RefKind.KEYWORD, a

        if (color := COLOR_BY_PLURAL.get(a)) is not None:
            return RefKind.COLOR, color.value
        # Singular color, e.g. `#gold`.
        if (color := COLOR_BY_PLURAL.get(a + "s")) is not None:
            return RefKind.COLOR, color.value

        for candidate in (a, a.removeprefix("the-"), a.rstrip("s")):
            if candidate in self._card_ids:
                return RefKind.CHARACTER, candidate

        raise UnresolvedAnchor(anchor)

    def refs(self, md: str) -> tuple[Ref, ...]:
        """Every distinct reference in `md`, in order of first appearance."""
        out: list[Ref] = []
        seen: set[tuple[RefKind, str]] = set()
        for label, anchor in LINK_RE.findall(md):
            kind, target = self.resolve(anchor)
            if kind is RefKind.KEYWORD:
                continue  # rules glossary, not a game object
            if (kind, target) in seen:
                continue
            seen.add((kind, target))
            out.append(Ref(kind=kind, label=label, target=target))
        return tuple(out)

    def ability(self, md: str | None) -> Ability | None:
        if md is None or not str(md).strip():
            return None
        md = str(md)
        return Ability(text=strip_links(md), raw=md, refs=self.refs(md))

    def bonuses(self, md: str | None) -> tuple[BonusClause, ...]:
        """Split an end-game bonus cell into its `N: condition` clauses."""
        if md is None or not str(md).strip():
            return ()
        out: list[BonusClause] = []
        for chunk in str(md).split("|"):
            raw = chunk.strip()
            if not raw:
                continue
            m = CLAUSE_RE.match(raw)
            if m is None:
                raise ValueError(f"unparseable end-game bonus clause: {raw!r}")
            pts_txt = m.group("pts")
            points = None if pts_txt == "?" else int(pts_txt.replace(MINUS, "-"))
            out.append(
                BonusClause(
                    points=points,
                    condition=strip_links(m.group("cond")),
                    raw=raw,
                    refs=self.refs(raw),
                )
            )
        return tuple(out)


def colors_referenced(refs: Iterable[Ref]) -> frozenset[Color]:
    return frozenset(Color(r.target) for r in refs if r.kind is RefKind.COLOR)


def characters_referenced(refs: Iterable[Ref]) -> frozenset[str]:
    return frozenset(r.target for r in refs if r.kind is RefKind.CHARACTER)
