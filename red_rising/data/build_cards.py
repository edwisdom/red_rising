"""Build `cards.json` from `red_rising_characters.parquet`.

Run from the repo root:

    uv run python -m red_rising.data.build_cards

This is the ONLY place pandas/pyarrow are used. The engine reads the JSON.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from red_rising.carddefs import CARDS_JSON, CardDef, CardIndex
from red_rising.data.parse import make_resolver
from red_rising.enums import Color

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARQUET = REPO_ROOT / "red_rising_characters.parquet"


def build(parquet: Path) -> CardIndex:
    import pandas as pd

    df = pd.read_parquet(parquet)
    resolver = make_resolver(df["id"].tolist())

    cards: list[CardDef] = []
    for row in df.itertuples(index=False):
        cards.append(
            CardDef(
                id=row.id,
                name=row.name,
                color=Color(row.color),
                role=row.role,
                core_value=int(row.core_value),
                deploy=resolver.ability(_none(row.deploy_ability)),
                block=resolver.ability(_none(row.block_ability)),
                endgame=resolver.ability(_none(row.end_game_abilities)),
                bonuses=resolver.bonuses(_none(row.end_game_bonuses)),
            )
        )

    # Stable order so the checked-in JSON has a clean diff between rebuilds.
    cards.sort(key=lambda c: c.id)
    return CardIndex(cards=tuple(cards))


def _none(value: object) -> str | None:
    """pandas gives NaN (a float) for empty cells; normalise to None."""
    if value is None:
        return None
    if isinstance(value, float):  # NaN
        return None
    text = str(value).strip()
    return text or None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    ap.add_argument("--out", type=Path, default=CARDS_JSON)
    args = ap.parse_args()

    index = build(args.parquet)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(index.model_dump_json(indent=2) + "\n")

    counts = {c: sum(1 for card in index if card.color is c) for c in Color}
    print(f"Wrote {len(index)} cards to {args.out.relative_to(REPO_ROOT)}")
    print("Color distribution:")
    for color, n in counts.items():
        flag = "" if (n == 7 or (color is Color.GOLD and n == 21)) else "  <-- unexpected"
        print(f"  {color.value:9s} {n:2d}{flag}")


if __name__ == "__main__":
    main()
