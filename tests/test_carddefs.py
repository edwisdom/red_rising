"""Phase 0: the card data pipeline.

These tests are the contract between the parquet and everything downstream. If
they pass, the engine can trust `load_cards()` completely.
"""

from __future__ import annotations

import pytest

from red_rising.carddefs import RefKind, load_cards
from red_rising.data.parse import UnresolvedAnchor, make_resolver, strip_links
from red_rising.enums import Color

CARDS = load_cards()


def test_full_deck_loads():
    assert len(CARDS) == 112


def test_color_distribution():
    """21 Golds, 7 of every other caste."""
    for color in Color:
        expected = 21 if color is Color.GOLD else 7
        assert len(CARDS.of_color(color)) == expected, color


def test_roles_agree_with_castes():
    # Enforced by CardDef's validator; asserted here so the failure is legible.
    for card in CARDS:
        assert card.role == card.color.caste, card.id


def test_every_character_ref_points_at_a_real_card():
    ids = set(CARDS.by_id)
    for card in CARDS:
        sources = [card.deploy, card.block, card.endgame, *card.bonuses]
        for source in sources:
            if source is None:
                continue
            for ref in source.refs:
                if ref.kind is RefKind.CHARACTER:
                    assert ref.target in ids, f"{card.id}: dangling ref {ref.target}"
                elif ref.kind is RefKind.COLOR:
                    Color(ref.target)  # raises if not a real color


def test_no_keyword_refs_leak_into_structured_refs():
    """`[banish](#banish)` is glossary prose, not a game object."""
    for card in CARDS:
        if card.deploy:
            assert all(r.kind is not RefKind.KEYWORD for r in card.deploy.refs)


def test_ability_text_has_no_markdown_left():
    for card in CARDS:
        for source in (card.deploy, card.block, card.endgame):
            if source is not None:
                assert "](#" not in source.text, card.id
        for bonus in card.bonuses:
            assert "](#" not in bonus.condition, card.id


def test_expected_ability_counts():
    """Locks in the survey the architecture was designed around."""
    assert sum(1 for c in CARDS if c.deploy) == 107
    assert sum(1 for c in CARDS if c.block) == 5
    assert sum(1 for c in CARDS if c.endgame) == 26
    assert sum(len(c.bonuses) for c in CARDS) == 127


def test_wildcards_are_exactly_gray_and_orange():
    assert sum(1 for c in CARDS if c.is_wild_color) == 7
    assert sum(1 for c in CARDS if c.is_wild_name) == 7
    # Every Gray has the wildcard-color end-game ability, every Orange the name one.
    for card in CARDS.of_color(Color.GRAY):
        assert card.endgame and "any one other color" in card.endgame.text
    for card in CARDS.of_color(Color.ORANGE):
        assert card.endgame and "same name as any specific character" in card.endgame.text


class TestAnchorResolution:
    resolver = make_resolver(CARDS.by_id)

    def test_plural_color(self):
        assert self.resolver.resolve("golds") == (RefKind.COLOR, "Gold")

    def test_singular_color(self):
        assert self.resolver.resolve("gold") == (RefKind.COLOR, "Gold")

    def test_the_prefix_is_stripped(self):
        """Anchors slugify the card *name*; ids drop the leading article."""
        assert self.resolver.resolve("the-jackal") == (RefKind.CHARACTER, "jackal")
        assert self.resolver.resolve("the-pax") == (RefKind.CHARACTER, "pax")
        assert self.resolver.resolve("the-howlers") == (RefKind.CHARACTER, "howlers")

    def test_pax_variants_stay_distinct(self):
        assert self.resolver.resolve("pax-au-telemanus")[1] == "pax-au-telemanus"
        assert self.resolver.resolve("the-pax")[1] == "pax"

    def test_keyword(self):
        assert self.resolver.resolve("banish") == (RefKind.KEYWORD, "banish")

    def test_unknown_anchor_raises(self):
        with pytest.raises(UnresolvedAnchor):
            self.resolver.resolve("not-a-real-card")


def test_strip_links():
    assert strip_links("[Banish](#banish) a [Gold](#golds).") == "Banish a Gold."


class TestBonusClauses:
    def test_negative_points_use_unicode_minus(self):
        antonia = CARDS["antonia"]
        assert [b.points for b in antonia.bonuses] == [15, -10]

    def test_variable_points_are_none(self):
        variable = [b for c in CARDS for b in c.bonuses if b.points is None]
        assert len(variable) == 2, "two cards print '?' for a computed award"

    def test_multi_clause_split(self):
        alfrun = CARDS["alfrun"]
        assert len(alfrun.bonuses) == 2
        assert {r.target for b in alfrun.bonuses for r in b.refs} == {"nero", "jopho"}


def test_cards_json_is_current(tmp_path):
    """Guards against editing the parquet and forgetting to rebuild."""
    pytest.importorskip("pandas")
    from red_rising.data.build_cards import DEFAULT_PARQUET, build

    rebuilt = build(DEFAULT_PARQUET)
    assert rebuilt == CARDS, (
        "cards.json is stale; run `uv run python -m red_rising.data.build_cards`"
    )
