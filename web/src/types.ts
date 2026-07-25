// Wire types — the shapes the FastAPI backend sends. Kept in sync with
// `red_rising/app/views.py` and `carddefs.py` by hand for now; a future step can
// generate these from the OpenAPI schema (openapi-typescript).

export interface Ref {
  kind: "color" | "character" | "keyword";
  label: string;
  target: string;
}
export interface Ability {
  text: string;
  raw: string;
  refs: Ref[];
}
export interface BonusClause {
  points: number | null;
  condition: string;
  raw: string;
  refs: Ref[];
}
export interface CardDef {
  id: string;
  name: string;
  color: string;
  role: string;
  core_value: number;
  deploy: Ability | null;
  block: Ability | null;
  endgame: Ability | null;
  bonuses: BonusClause[];
  art_url: string | null;
}

export interface Option {
  token: string;
  label: string;
  card_id: string | null;
  location: string | null;
  seat: string | null;
  tag: string | null;
}
export interface PendingDecision {
  id: number;
  seat: string;
  prompt: string;
  options: Option[];
  min_choices: number;
  max_choices: number;
  kind: string;
}

export interface CardSlot {
  card_id: string | null;
  face_down: boolean;
}
export interface LocationView {
  location: string;
  cards: CardSlot[];
}
export interface SelfView {
  seat: string;
  name: string;
  house: string;
  hand: string[];
  helium: number;
  fleet: number;
  influence_on_institute: number;
  influence_supply: number;
  has_sovereign: boolean;
}
export interface OpponentView {
  seat: string;
  name: string;
  house: string;
  hand_count: number;
  helium: number;
  fleet: number;
  influence_on_institute: number;
  influence_supply: number;
  has_sovereign: boolean;
}
export interface WaitingOn {
  seat: string;
  name: string;
  prompt: string;
}
export interface ScoreBreakdown {
  seat: string;
  core_values: number;
  card_bonuses: number;
  fleet: number;
  helium: number;
  sovereignty: number;
  influence: number;
  excess_penalty: number;
}
export interface PlayerView {
  game_id: string;
  seat: string;
  turn_number: number;
  current_player_seat: string | null;
  first_player_seat: string;
  you: SelfView;
  opponents: OpponentView[];
  locations: LocationView[];
  deck_count: number;
  banished: string[];
  sovereign_holder: string | null;
  neutral_influence: number;
  pending: PendingDecision | null;
  waiting_on: WaitingOn | null;
  finished: boolean;
  scores: Record<string, ScoreBreakdown> | null;
  last_seq: number;
}

// Score totals aren't sent; derive from the breakdown.
export function scoreTotal(s: ScoreBreakdown): number {
  return (
    s.core_values +
    s.card_bonuses +
    s.fleet +
    s.helium +
    s.sovereignty +
    s.influence +
    s.excess_penalty
  );
}

export const FLEET_TRACK_POINTS = [0, 1, 3, 6, 10, 15, 21, 28, 34, 39, 43];
