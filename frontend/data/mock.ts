export interface Match {
  id: number;
  home: string;
  away: string;
  league: string;
  time: string;
  divergence: number;
  confidence: number;
  risk: "faible" | "modéré" | "élevé";
  locked: boolean;
  odds: { home: number; draw: number; away: number };
}

export const mockMatches: Match[] = [
  {
    id: 1,
    home: "PSG",
    away: "Marseille",
    league: "Ligue 1",
    time: "21h00",
    divergence: 11.3,
    confidence: 74,
    risk: "faible",
    locked: false,
    odds: { home: 1.72, draw: 3.5, away: 4.2 },
  },
  {
    id: 2,
    home: "Real Madrid",
    away: "Sevilla",
    league: "La Liga",
    time: "20h00",
    divergence: 8.7,
    confidence: 68,
    risk: "modéré",
    locked: false,
    odds: { home: 1.55, draw: 4.1, away: 5.5 },
  },
  {
    id: 3,
    home: "Bayern",
    away: "Leverkusen",
    league: "Bundesliga",
    time: "18h30",
    divergence: 7.1,
    confidence: 63,
    risk: "modéré",
    locked: false,
    odds: { home: 1.88, draw: 3.6, away: 3.9 },
  },
  {
    id: 4,
    home: "Arsenal",
    away: "Chelsea",
    league: "Premier League",
    time: "17h30",
    divergence: 9.4,
    confidence: 71,
    risk: "modéré",
    locked: true,
    odds: { home: 2.1, draw: 3.3, away: 3.4 },
  },
  {
    id: 5,
    home: "Inter Milan",
    away: "Juventus",
    league: "Serie A",
    time: "20h45",
    divergence: 6.8,
    confidence: 65,
    risk: "modéré",
    locked: true,
    odds: { home: 2.0, draw: 3.2, away: 3.6 },
  },
  {
    id: 6,
    home: "Barcelona",
    away: "Atlético",
    league: "La Liga",
    time: "21h00",
    divergence: 12.1,
    confidence: 78,
    risk: "faible",
    locked: true,
    odds: { home: 1.65, draw: 3.8, away: 4.8 },
  },
];
