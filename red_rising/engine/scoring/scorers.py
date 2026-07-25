"""Per-card end-game bonus scorers.

Every card with printed end-game bonus points (🏆) has a `@score(id)` function that
returns its total for a given `ScoreCtx`. Written to read against the card text
(quoted in the docstring); the compound "and/or/but-not-both/another/only" logic the
data can't express generically is spelled out here, honestly, one card at a time.

The color one-letter aliases keep the common `for_each`/`if_with` lines short.
"""

from __future__ import annotations

from collections.abc import Callable

from red_rising.enums import Color

from .context import ScoreCtx

Scorer = Callable[[ScoreCtx], int]
SCORERS: dict[str, Scorer] = {}


def score(card_id: str) -> Callable[[Scorer], Scorer]:
    def register(fn: Scorer) -> Scorer:
        if card_id in SCORERS:
            raise ValueError(f"duplicate scorer for {card_id}")
        SCORERS[card_id] = fn
        return fn

    return register


# Caste aliases.
RED, PINK, ORANGE, YELLOW, GREEN, COPPER = (
    Color.RED,
    Color.PINK,
    Color.ORANGE,
    Color.YELLOW,
    Color.GREEN,
    Color.COPPER,
)
SILVER, GOLD, BLUE, VIOLET, WHITE, GRAY, BROWN, OBSIDIAN = (
    Color.SILVER,
    Color.GOLD,
    Color.BLUE,
    Color.VIOLET,
    Color.WHITE,
    Color.GRAY,
    Color.BROWN,
    Color.OBSIDIAN,
)


# --------------------------------------------------------------------------- #
# "for each …"
# --------------------------------------------------------------------------- #

score("artisan-chef")(lambda s: 5 * s.for_each(GOLD))
score("assassin")(lambda s: 10 * s.for_each(OBSIDIAN))
score("gardener")(lambda s: 5 * s.for_each(VIOLET, PINK))
score("janitor")(lambda s: 5 * s.for_each(GREEN, YELLOW, BLUE))
score("mess-hall-cook")(lambda s: 5 * s.for_each(GRAY, ORANGE))
score("modjob")(lambda s: 5 * s.for_each(RED, BROWN))  # "including Modjob"
score("nanny")(lambda s: 5 * s.for_each(SILVER, WHITE, COPPER))
score("roque")(lambda s: 5 * s.for_each(BLUE))
score("surgeon")(lambda s: 5 * s.for_each(GOLD))
score("judge")(lambda s: 3 * s.n_cards)  # "for each of your cards"
score("mustang")(lambda s: 5 * len({s.cards[c].color for c in s.hand_ids}))  # each diff color
score("sefi")(lambda s: s.pts(s.has("ragnar"), 20) - 5 * s.for_each(GOLD))

# "for each … on all locations" (board, not hand)
score("bridge")(lambda s: 5 * s.count_on_board(PINK, VIOLET))
score("colonel-valentin")(lambda s: 5 * s.count_on_board(GOLD))
score("danto")(lambda s: 5 * s.count_on_board(COPPER, WHITE))
score("holiday")(lambda s: 5 * s.count_on_board(ORANGE, BLUE))
score("sun-hwa")(lambda s: 5 * s.count_on_board(OBSIDIAN, GREEN))
score("trigg")(lambda s: 5 * s.count_on_board(GRAY, YELLOW))
score("ugly-dan")(lambda s: 5 * s.count_on_board(RED, BROWN))

# per-token
score("sponsor")(lambda s: 2 * s.influence)
score("timony")(lambda s: 3 * s.influence)
score("stock-broker")(lambda s: min(25, 5 * s.helium))

# banished
score("ash-lord")(lambda s: 5 * s.for_each(BLUE) + 5 * s.count_banished(BLUE))
score("group-counselor")(lambda s: -1 * s.banished_count)


# --------------------------------------------------------------------------- #
# Simple "if with <color/name>" (OR of targets)
# --------------------------------------------------------------------------- #

score("aja")(lambda s: s.pts(s.has("octavia"), 15))
score("boneriders")(lambda s: s.pts(s.has("jackal", GRAY), 15))
score("calliope")(lambda s: s.pts(s.has("jackal"), 20))
score("conversationalist")(lambda s: s.pts(s.has(WHITE), 15))
score("cyther")(lambda s: s.pts(s.has(BLUE), 16))
score("dataport-specialist")(lambda s: s.pts(s.has(BLUE), 26))
score("garden-trained-rose")(lambda s: s.pts(s.has(SILVER), 14))
score("gravboot-cobbler")(lambda s: s.pts(s.has(GOLD, GRAY), 14))
score("helga")(lambda s: s.pts(s.has("pax-au-telemanus", "pax"), 16))
score("holo-designer")(lambda s: s.pts(s.has(VIOLET), 28))
score("howlers")(lambda s: s.pts(s.has("sevro"), 15))
score("masseuse")(lambda s: s.pts(s.has(COPPER), 16))
score("matteo")(lambda s: s.pts(s.has(PINK, "quicksilver"), 17))
score("orion")(lambda s: s.pts(s.has("pax-au-telemanus", "pax"), 10) + s.fleet)
score("pax")(lambda s: s.pts(s.has("darrow", "sevro", "orion", "virga", "pelus"), 15))
score("pax-au-telemanus")(lambda s: s.pts(s.has(OBSIDIAN, "mustang"), 20))
score("pulse-armorer")(lambda s: s.pts(s.has(GRAY), 17))
score("pulse-fistengineer")(lambda s: s.pts(s.has(OBSIDIAN), 18))
score("ragnar")(lambda s: s.pts(s.has(ORANGE), 10) + s.pts(s.has("sefi"), 10))
score("sevro")(lambda s: s.pts(s.has("victra", "howlers", RED), 20))
score("tactus")(lambda s: s.pts(s.has("octavia", "darrow", PINK), 20))
score("telemanuses")(lambda s: s.pts(s.has("pax-au-telemanus", "pax"), 15))
score("aegis-craftsman")(lambda s: s.pts(s.has(GOLD), 10) + s.pts(not s.has(OBSIDIAN), 10))
score("alfrun")(lambda s: s.pts(s.has("nero"), 10) + s.pts(s.has("jopho"), 10))
score("bondilus")(lambda s: s.pts(s.has_sovereign, 5) + s.pts(s.has(GOLD), 5))
score("evey")(lambda s: s.pts(s.has("darrow"), 15) + s.pts(s.has("mickey-the-carver"), -15))
score("fitchner")(lambda s: s.pts(s.has(RED), 10) + s.pts(s.has("sevro"), 10))
score("jopho")(lambda s: s.pts(s.has("alfrun"), 10) + s.pts(s.has("nero"), 10))
score("karnus")(
    lambda s: s.pts(s.has("cassius"), 30) + s.pts(s.has("mustang", "jackal", "nero"), -15)
)
score("victra")(lambda s: s.pts(s.has("howlers"), 10) + s.pts(s.has("sevro", "darrow"), 10))


# --------------------------------------------------------------------------- #
# "if with no …" / negative color conditions
# --------------------------------------------------------------------------- #

score("arlus")(lambda s: s.pts(not s.has(GOLD), 25))
score("dancer")(lambda s: s.pts(not s.has(GRAY), 11) + s.pts(not s.has(GOLD), 11))
score("deanna")(lambda s: s.pts(s.has_other(RED), 26))  # "another Red"
score("lorn")(lambda s: s.pts(not s.has_other(GOLD), 15))  # "no other Golds"


# --------------------------------------------------------------------------- #
# Compound (and / or / xor / "but not both" / "only")
# --------------------------------------------------------------------------- #


@score("antonia")
def antonia(s: ScoreCtx) -> int:
    """15 if with The Jackal or 2 other Golds. // -10 if with Victra or Sevro."""
    a = s.pts(s.has("jackal") or s.count(GOLD, exclude_self=True) >= 2, 15)
    return a + s.pts(s.has("victra", "sevro"), -10)


@score("artificer")
def artificer(s: ScoreCtx) -> int:
    """20 if with both another Orange and a Gold."""
    return s.pts(s.has_other(ORANGE) and s.has(GOLD), 20)


@score("cassius")
def cassius(s: ScoreCtx) -> int:
    """40 if with both Mustang & Darrow. // -20 if with Darrow (but not Mustang)."""
    both = s.pts(s.has("mustang") and s.has("darrow"), 40)
    return both + s.pts(s.has("darrow") and not s.has("mustang"), -20)


@score("razor-designer")
def razor_designer(s: ScoreCtx) -> int:
    """13 if with a Gold and no Obsidians."""
    return s.pts(s.has(GOLD) and not s.has(OBSIDIAN), 13)


@score("theodora")
def theodora(s: ScoreCtx) -> int:
    """14 if with a Gold or Red (but not both)."""
    return s.pts(s.has(GOLD) != s.has(RED), 14)


@score("romulus")
def romulus(s: ScoreCtx) -> int:
    """15 if Sovereign. // -25 if with Roque or Octavia or without a Blue."""
    good = s.pts(s.has_sovereign, 15)
    return good + s.pts(s.has("roque", "octavia") or not s.has(BLUE), -25)


@score("jackal")
def jackal(s: ScoreCtx) -> int:
    """30 if Sovereign. // -30 if with Darrow or Octavia."""
    return s.pts(s.has_sovereign, 30) + s.pts(s.has("darrow", "octavia"), -30)


@score("nero")
def nero(s: ScoreCtx) -> int:
    """10 if Sovereign. // -5 each for Cassius, Karnus, and Octavia."""
    penalty = -5 * s.count("cassius", "karnus", "octavia")
    return s.pts(s.has_sovereign, 10) + penalty


@score("lawyer")
def lawyer(s: ScoreCtx) -> int:
    """12 if with a White (not the Judge). // 22 if with the Judge."""
    white_non_judge = any(c != "judge" and WHITE in s._colors(c) for c in s.hand_ids)
    return s.pts(white_non_judge, 12) + s.pts(s.has("judge"), 22)


@score("morning-star")
def morning_star(s: ScoreCtx) -> int:
    """-15 unless with Orion, Virga, or Pelus."""
    return s.pts(not s.has("orion", "virga", "pelus"), -15)


@score("stained")
def stained(s: ScoreCtx) -> int:
    """15 if this is your only Obsidian."""
    return s.pts(s.count(OBSIDIAN) == 1, 15)


# "only with <colors>" — every card's printed color is in the set
score("alia-snowsparrow")(lambda s: s.pts(s.all_cards_are(GOLD, GRAY, OBSIDIAN), 24))
score("harmony")(lambda s: s.pts(s.all_cards_are(RED, PINK, BROWN, OBSIDIAN), 33))
score("priestess")(lambda s: s.pts(s.all_cards(lambda c: c.core_value >= 20), 20))
score("uncle-narol")(lambda s: s.pts(s.all_cards(lambda c: c.core_value <= 10), 40))


# --------------------------------------------------------------------------- #
# Hand-shape conditions
# --------------------------------------------------------------------------- #

score("4d-painter")(lambda s: s.pts(s.distinct_colors(), 31))
score("codebreaker")(lambda s: s.pts(s.distinct_initials(), 22))
score("musician")(lambda s: s.pts(all(v % 2 == 0 for v in s.core_values()), 32))
score("zanzibar")(lambda s: s.pts(all(v % 2 == 1 for v in s.core_values()), 31))
score("darrow")(lambda s: s.pts(s.n_cards >= 7, 30))
score("loan-shark")(lambda s: s.pts(s.n_cards >= 7, 7))


# --------------------------------------------------------------------------- #
# Sovereign / tokens
# --------------------------------------------------------------------------- #

score("seer")(lambda s: s.pts(s.has_sovereign, 11))
score("orator")(lambda s: s.pts(not s.has_sovereign, 21))
score("lysander")(lambda s: s.pts(s.has_sovereign or s.has("octavia", "cassius"), 20))
score("octavia")(lambda s: s.pts(not (s.has_sovereign or s.has("lysander")), -30))
score("ceo")(lambda s: s.pts(s.helium >= 5, 18))
score("magistrate")(lambda s: s.pts(s.helium >= 3 and s.influence >= 3 and s.fleet >= 3, 15))


# --------------------------------------------------------------------------- #
# Cross-player ranks
# --------------------------------------------------------------------------- #

score("holo-host")(lambda s: s.pts(s.most_influence, 18))
score("politician")(lambda s: s.pts(s.most_influence, 15))
score("quietus")(lambda s: s.pts(s.most_influence, 16))
score("administrator")(lambda s: s.pts(s.least_influence, 15))
score("reporter")(lambda s: s.pts(s.most_helium, 29))
score("quicksilver")(lambda s: s.pts(s.opp_more_helium, -30))
score("vlogger")(lambda s: s.pts(s.most_fleet, 23))
score("diplomat")(lambda s: s.pts(s.ties_influence_with_opp, 19))
score("invictus")(lambda s: s.pts(s.most_fleet, 16) + s.pts(s.opp_more_fleet, -9))


# --------------------------------------------------------------------------- #
# Fleet-position bands
# --------------------------------------------------------------------------- #

score("pelus")(lambda s: 20 if 5 <= s.fleet <= 7 else 35 if s.fleet >= 8 else 0)
score("virga")(lambda s: 15 if 6 <= s.fleet <= 8 else 30 if s.fleet >= 9 else 0)


# --------------------------------------------------------------------------- #
# Banished-pile size / contents
# --------------------------------------------------------------------------- #

score("pathologist")(lambda s: 25 if s.banished_count >= 10 else 10 if s.banished_count >= 5 else 0)
score("researcher")(lambda s: s.pts(s.banished_count <= 4, 17))
score("mickey-the-carver")(lambda s: s.pts(s.banished_has_color(RED), 10) + s.pts(s.has(GOLD), 10))
score("firewall-expert")(lambda s: s.pts(s.a_location_empty_or_facedown, 22))


# --------------------------------------------------------------------------- #
# Variable ("?") clauses
# --------------------------------------------------------------------------- #

score("developer")(lambda s: s.max_location_top_core())  # gain core of a location top


@score("eo")  # override the placeholder; eo also has "-10 if with a Gray (except Bridge)"
def eo(s: ScoreCtx) -> int:
    """10 for each other Red. // -10 if with a Gray (except Bridge)."""
    each = 10 * s.for_each(RED, exclude_self=True)
    gray_non_bridge = any(c != "bridge" and GRAY in s._colors(c) for c in s.hand_ids)
    return each + s.pts(gray_non_bridge, -10)
