export type Outcome = "home" | "draw" | "away";
export type Probs = { home: number; draw: number; away: number };
export type Plan = "STARTER" | "PRO" | "ELITE";

export type Favourite = { outcome: Outcome; label: string; prob: number; source: string };
export type BestGap = { bookmaker: string; outcome: Outcome; gap: number; odds: number };
// Score le plus probable déduit du marché (Poisson calibré, cf. docs/mesures/2026-09-11-score-le-plus-probable.md) :
// "score" est de la forme "2-1", "probability" sa probabilité (0-1).
export type ScoreProbability = { score: string; probability: number };
export type TopScore = ScoreProbability;

export type MatchSummary = {
  id: string; competition: string; league: string; home_team: string; away_team: string;
  kickoff_at: string; status: "SCHEDULED" | "LIVE" | "FINISHED" | "POSTPONED";
  favourite: Favourite | null; reference: Probs | null; best_gap: BestGap | null;
  movement: Probs | null; odds_taken_at: string | null; locked: boolean;
  top_score: TopScore | null;
};

export type Book = { bookmaker: string; label: string; home: number; draw: number; away: number; margin: number; gaps: Probs };
export type Form = { played: number; wins: number; draws: number; losses: number; goals_for: number; goals_against: number; sequence: string };
export type H2H = { kickoff_at: string; home: string; away: string; score: string };

// Total de buts attendu utilisé pour calculer le score le plus probable : "marché" (over/under Pinnacle,
// cf. docs/mesures/2026-09-11-score-le-plus-probable.md, complément du 11/09/2026) ou repli "ligue" (moyenne).
export type ExpectedGoals = { total: number; source: "marché" | "ligue" };

export type MatchDetail = MatchSummary & {
  books: Book[] | null;
  reference_book: { bookmaker: string; label: string; home: number; draw: number; away: number; margin: number } | null;
  history: { taken_at: string; reference: Probs }[] | null;
  form: { home: Form; away: Form }; h2h: H2H[]; analysis: string | null;
  result: { home: number; away: number } | null;
  score_distribution: ScoreProbability[] | null;   // les 5 scores les plus probables, réservé au pro
  expected_goals: ExpectedGoals | null;             // public, même verrouillé
};

export type BookRow = { bookmaker: string; label: string; matches: number; avg_margin: number | null; gaps_above_threshold: number;
  best: { match_id: string; home_team: string; away_team: string; kickoff_at: string; outcome: Outcome; gap: number; odds: number } | null };

export type TrackRow = { competition: string; played: number; favourite_won: number; favourite_rate: number };

export type Bet = { id: string; match_id: string; home_team: string; away_team: string; competition: string; kickoff_at: string;
  outcome: Outcome; bookmaker: string; odds: number; stake: number; status: "PENDING" | "WON" | "LOST" | "VOID"; payout: number | null;
  created_at: string; settled_at: string | null; match_status: "SCHEDULED" | "LIVE" | "FINISHED" | "POSTPONED" | "QUARANTINE" };
export type BankrollSummary = { stakes: number; settled_stakes: number; payouts: number; profit: number; roi: number | null; pending: number; settled: number;
  by_bookmaker: Record<string, { stakes: number; payouts: number; profit: number; bets: number }>;
  by_competition: Record<string, { stakes: number; payouts: number; profit: number; bets: number }> };

export type User = { id: string; first_name: string; email: string; role: string; subscription_plan: Plan };
export type Legal = { warning: string; minimum_age: number; positioning: string };
export type Pagination = { page: number; limit: number; total: number };

export const COMPETITIONS: Record<string, string> = {
  E0: "Premier League", F1: "Ligue 1", SP1: "Liga", D1: "Bundesliga", I1: "Serie A", CL: "Ligue des Champions", EL: "Ligue Europa",
};
export const BOOK_LABELS: Record<string, string> = {
  betclic_fr: "Betclic", winamax_fr: "Winamax", unibet_fr: "Unibet", pmu_fr: "PMU", netbet_fr: "NetBet", pinnacle: "Pinnacle",
};
