import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DayPicker } from "@/components/DayPicker";
import { CompetitionFilter } from "@/components/CompetitionFilter";
import { parisDate } from "@/lib/format";

describe("DayPicker", () => {
  it("7 jours, date et compétition préservées dans les liens, aria-current sur le jour sélectionné", () => {
    const today = parisDate();
    render(<DayPicker selected={today} competition="F1" />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(7);
    links.forEach((l) => expect(l).toHaveAttribute("href", expect.stringContaining("&competition=F1")));
    const selected = links.find((l) => l.getAttribute("href")?.includes(`date=${today}`));
    expect(selected).toHaveAttribute("aria-current", "page");
    links.filter((l) => l !== selected).forEach((l) => expect(l).not.toHaveAttribute("aria-current"));
  });
});

describe("CompetitionFilter", () => {
  it("« Tous » + 19 compétitions, date préservée dans les liens, aria-current sur la compétition sélectionnée", () => {
    render(<CompetitionFilter date="2026-09-13" selected="F1" />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(20);
    expect(screen.getByText("Tous")).toBeInTheDocument();
    links.forEach((l) => expect(l).toHaveAttribute("href", expect.stringContaining("date=2026-09-13")));
    const selected = screen.getByText("Ligue 1").closest("a");
    expect(selected).toHaveAttribute("aria-current", "page");
    links.filter((l) => l !== selected).forEach((l) => expect(l).not.toHaveAttribute("aria-current"));
  });

  it("les compétitions sont groupées, avec un libellé par groupe", () => {
    // Vingt pastilles sur une seule ligne défilante ne se lisent plus : le groupe dit où chercher.
    render(<CompetitionFilter date="2026-09-13" />);
    expect(screen.getByText("Top 5")).toBeInTheDocument();
    expect(screen.getByText("Coupes d'Europe et sélections")).toBeInTheDocument();
    expect(screen.getByText("Autres championnats")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ligue des Nations" })).toHaveAttribute("href", "/matchs?date=2026-09-13&competition=NL");
    expect(screen.getByRole("link", { name: "Championship" })).toBeInTheDocument();
  });
});
