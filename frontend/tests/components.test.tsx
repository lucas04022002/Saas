import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BigNumber } from "@/components/BigNumber";
import { Bars, outcomeRows } from "@/components/Bars";
import { MatchRow } from "@/components/MatchRow";
import { Reserved } from "@/components/Reserved";
import type { MatchSummary } from "@/lib/types";

const base: MatchSummary = {
  id: "m1", competition: "F1", league: "Ligue 1", home_team: "Lyon", away_team: "Marseille", kickoff_at: "2026-09-13T15:15:00Z", status: "SCHEDULED",
  favourite: { outcome: "home", label: "Lyon", prob: 0.58, source: "pinnacle" }, reference: { home: 0.58, draw: 0.24, away: 0.18 },
  best_gap: { bookmaker: "betclic_fr", outcome: "home", gap: 0.032, odds: 1.78 }, movement: { home: 3.1, draw: -1.2, away: -1.9 },
  odds_taken_at: "2026-09-13T10:00:00Z", locked: false, top_score: { score: "2-1", probability: 0.12 },
};

describe("BigNumber", () => {
  it("affiche la valeur finale sans IntersectionObserver", () => {
    render(<BigNumber value={58} suffix="%" />);
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("%")).toBeInTheDocument();
  });
});

describe("Bars", () => {
  it("trois lignes avec les valeurs en pourcentage entier", () => {
    render(<Bars rows={outcomeRows(base.reference!, "home", "Lyon", "Marseille")} />);
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(screen.getByText("Marseille")).toBeInTheDocument();
  });
  it("scores : lignes libres, la plus probable surlignée", () => {
    render(<Bars rows={[{ key: "2-1", label: "2-1", value: 0.12, highlight: true }, { key: "1-1", label: "1-1", value: 0.1 }]} />);
    expect(screen.getByText("2-1")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });
});

describe("MatchRow", () => {
  it("abonné : écart et mouvement visibles, chiffre et favori", () => {
    render(<MatchRow match={base} />);
    expect(screen.getByText("Lyon – Marseille")).toBeInTheDocument();
    expect(screen.getByText("Betclic +3,2 %")).toBeInTheDocument();
    expect(screen.getByText("▲ 3 pts")).toBeInTheDocument();
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("Lyon favori")).toBeInTheDocument();
    expect(screen.getByText("2-1")).toBeInTheDocument();
    expect(screen.getByText("score le plus probable")).toBeInTheDocument();
  });
  it("verrouillé : rien de chiffré, et aucun état inventé", () => {
    render(
      <MatchRow
        match={{ ...base, locked: true, favourite: null, reference: null, best_gap: null, movement: null, top_score: null }}
      />,
    );

    expect(screen.getAllByText("Réservé").length).toBe(2); // écarts et mouvement
    expect(screen.queryByText(/Betclic/)).not.toBeInTheDocument();
    expect(screen.queryByText("2-1")).not.toBeInTheDocument();
    expect(screen.getByText("Verrouillé")).toBeInTheDocument();
    expect(screen.getByText("à ouvrir")).toBeInTheDocument();

    // Deux affirmations qui seraient fausses : la donnée existe, elle est réservée.
    expect(screen.queryByText("stable")).not.toBeInTheDocument();
    expect(screen.queryByText("pas encore de relevé")).not.toBeInTheDocument();
  });
  it("match serré : libellé « serré » et pas de couleur favori", () => {
    render(<MatchRow match={{ ...base, favourite: { outcome: "home", label: "Lens", prob: 0.41, source: "pinnacle" }, reference: { home: 0.41, draw: 0.3, away: 0.29 } }} />);
    expect(screen.getByText("Lens, serré")).toBeInTheDocument();
  });
  it("sans relevé : tiret et « pas encore de relevé »", () => {
    render(<MatchRow match={{ ...base, favourite: null, reference: null, best_gap: null, movement: null, odds_taken_at: null, top_score: null }} />);
    expect(screen.getByText("pas encore de relevé")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});

describe("Reserved", () => {
  it("lien vers les tarifs", () => {
    render(<Reserved />);
    expect(screen.getByRole("link", { name: /Réservé aux abonnés/ })).toHaveAttribute("href", "/tarifs");
  });
});
