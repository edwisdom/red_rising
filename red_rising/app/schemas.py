"""Request/response bodies for the REST surface."""

from __future__ import annotations

from pydantic import BaseModel, Field

from red_rising.enums import House


class NewPlayer(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    house: House | None = None


class CreateGameRequest(BaseModel):
    players: list[NewPlayer] = Field(min_length=2, max_length=6)
    seed: int | None = None


class SeatOut(BaseModel):
    seat: str
    name: str
    token: str


class CreateGameResponse(BaseModel):
    game_id: str
    seats: list[SeatOut]


class SubmitAnswer(BaseModel):
    decision_id: int
    tokens: list[str]
