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

/**
 * L'état du quota hebdomadaire, tel que le serveur le calcule.
 *
 * `limit` et `remaining` valent `null` pour un abonné : il n'a pas de quota,
 * et afficher « 0 restant » serait mensonger. `ANONYMOUS` n'a droit à rien
 * tant qu'il n'a pas de compte.
 */
export type Quota = {
  plan: "ANONYMOUS" | "STARTER" | "PRO";
  limit: number | null;
  used: number;
  remaining: number | null;
  resets_at: string | null;
};

export type TrackRow = { competition: string; played: number; favourite_won: number; favourite_rate: number };

export type Bet = { id: string; match_id: string; home_team: string; away_team: string; competition: string; kickoff_at: string;
  outcome: Outcome; bookmaker: string; odds: number; stake: number; status: "PENDING" | "WON" | "LOST" | "VOID"; payout: number | null;
  created_at: string; settled_at: string | null; match_status: "SCHEDULED" | "LIVE" | "FINISHED" | "POSTPONED" | "QUARANTINE" };
export type BankrollSummary = { stakes: number; settled_stakes: number; payouts: number; profit: number; roi: number | null; pending: number; settled: number;
  by_bookmaker: Record<string, { stakes: number; payouts: number; profit: number; bets: number }>;
  by_competition: Record<string, { stakes: number; payouts: number; profit: number; bets: number }> };

/** L'état de l'abonnement, tel que le dernier webhook Stripe l'a laissé. */
export type Abonnement = {
  plan: string;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
};
export type User = { id: string; first_name: string; email: string; role: string; subscription_plan: Plan };
export type Legal = { warning: string; minimum_age: number; positioning: string };
export type Pagination = { page: number; limit: number; total: number };

/**
 * Le catalogue des compétitions, groupé comme il s'affiche.
 *
 * Les groupes sont la source unique : les libellés (`COMPETITIONS`) et l'ordre
 * d'affichage (`COMPETITION_ORDER`) en dérivent. Deux listes tenues à la main
 * finissent par diverger, et une compétition présente dans l'une mais pas dans
 * l'autre serait renvoyée par l'API, comptée nulle part et jamais montrée.
 *
 * Les codes sont ceux de l'API (= football-data.co.uk) ; le libellé est celui
 * que lit un lecteur français.
 */
export const COMPETITION_GROUPS: readonly (readonly [string, readonly (readonly [string, string])[]])[] = [
  ["Top 5", [["F1", "Ligue 1"], ["E0", "Premier League"], ["SP1", "Liga"], ["D1", "Bundesliga"], ["I1", "Serie A"]]],
  ["Coupes d'Europe et sélections", [["CL", "Ligue des Champions"], ["EL", "Ligue Europa"], ["NL", "Ligue des Nations"]]],
  [
    "Autres championnats",
    [
      ["E1", "Championship"], ["F2", "Ligue 2"], ["SP2", "Liga 2"], ["D2", "2. Bundesliga"], ["I2", "Serie B"],
      ["N1", "Eredivisie"], ["P1", "Liga Portugal"], ["B1", "Pro League belge"], ["T1", "Süper Lig"],
      ["G1", "Super League grecque"], ["SC0", "Premiership écossaise"],
    ],
  ],
] as const;

export const COMPETITIONS: Record<string, string> = Object.fromEntries(
  COMPETITION_GROUPS.flatMap(([, entries]) => entries.map(([code, label]) => [code, label])),
);

/** L'ordre d'affichage des groupes de matchs : celui du catalogue. */
export const COMPETITION_ORDER: readonly string[] = COMPETITION_GROUPS.flatMap(([, entries]) => entries.map(([code]) => code));
export const BOOK_LABELS: Record<string, string> = {
  betclic_fr: "Betclic", winamax_fr: "Winamax", unibet_fr: "Unibet", pmu_fr: "PMU", netbet_fr: "NetBet", pinnacle: "Pinnacle",
};
