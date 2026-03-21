"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Section } from "../../ui/section";

const BETS = [
  { odds: 1.74, win: true },
  { odds: 1.89, win: false },
  { odds: 1.58, win: true },
  { odds: 1.72, win: true },
  { odds: 1.95, win: false },
  { odds: 1.65, win: true },
  { odds: 1.8, win: true },
  { odds: 2.1, win: false },
  { odds: 1.55, win: true },
  { odds: 1.68, win: true },
  { odds: 1.75, win: false },
  { odds: 1.62, win: true },
  { odds: 1.9, win: true },
  { odds: 1.45, win: true },
  { odds: 2.05, win: false },
  { odds: 1.7, win: true },
  { odds: 1.85, win: false },
  { odds: 1.6, win: true },
  { odds: 1.78, win: true },
  { odds: 1.95, win: true },
  { odds: 1.52, win: false },
  { odds: 1.65, win: true },
  { odds: 1.88, win: false },
  { odds: 1.72, win: true },
  { odds: 1.58, win: true },
  { odds: 2.0, win: false },
  { odds: 1.67, win: true },
  { odds: 1.74, win: true },
  { odds: 1.82, win: true },
  { odds: 1.9, win: false },
];

function buildChartData() {
  let capital = 100;
  const data = [{ label: "Départ", capital: 100, win: null as boolean | null }];
  BETS.forEach((bet, i) => {
    if (bet.win) {
      capital = Math.round((capital + (bet.odds - 1) * 10) * 100) / 100;
    } else {
      capital = Math.round((capital - 10) * 100) / 100;
    }
    const dayLabel = (i + 1) % 3 === 0 ? `J${i + 1}` : "";
    data.push({ label: dayLabel, capital, win: bet.win });
  });
  return data;
}

const chartData = buildChartData();
const finalCapital = chartData[chartData.length - 1].capital;
const roi = Math.round(((finalCapital - 100) / 100) * 10000) / 100;

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { value: number }[];
}) {
  if (active && payload && payload.length) {
    return (
      <div
        style={{
          background: "#0F1118",
          border: "1px solid rgba(200,240,0,0.3)",
          borderRadius: 8,
          padding: "8px 12px",
        }}
      >
        <span style={{ color: "#C8F000", fontFamily: "var(--font-mono)", fontSize: 13 }}>
          Capital : {payload[0].value.toFixed(2)} €
        </span>
      </div>
    );
  }
  return null;
}

function CustomDot(props: {
  cx?: number;
  cy?: number;
  payload?: { win: boolean | null };
}) {
  const { cx, cy, payload } = props;
  if (!payload || payload.win !== false) return null;
  return <circle cx={cx} cy={cy} r={3} fill="#EF4444" stroke="none" />;
}

export default function CapitalChart({ className }: { className?: string }) {
  return (
    <Section className={className}>
      <div className="max-w-container mx-auto flex flex-col items-center gap-10">
        <div className="flex flex-col items-center gap-4 text-center">
          <h2
            className="text-3xl leading-tight font-semibold sm:text-5xl sm:leading-tight"
            style={{ fontFamily: "var(--font-heading, sans-serif)" }}
          >
            La transparence comme argument
          </h2>
          <p className="text-muted-foreground max-w-[520px] text-lg">
            Les gains et les pertes. Tout est visible.
          </p>
        </div>

        <div className="glass-2 w-full rounded-2xl p-6 flex flex-col gap-6">
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Capital départ", value: "100 €", highlight: false },
              { label: "Capital simulé", value: `${finalCapital.toFixed(2)} €`, highlight: false },
              {
                label: "ROI total",
                value: `${roi >= 0 ? "+" : ""}${roi} %`,
                highlight: true,
              },
              { label: "Mise constante", value: "10 €", highlight: false },
            ].map((kpi) => (
              <div
                key={kpi.label}
                className="rounded-xl border border-[#1E2D42] bg-[#0A1220] p-4 flex flex-col gap-1"
              >
                <div className="text-xs text-[#7A8FA8]">{kpi.label}</div>
                <div
                  className="text-xl font-semibold font-[family-name:var(--font-mono)]"
                  style={{ color: kpi.highlight ? "#C8F000" : "#DDD5C4" }}
                >
                  {kpi.value}
                </div>
              </div>
            ))}
          </div>

          {/* Chart */}
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" vertical={false} />
              <ReferenceLine
                y={100}
                stroke="rgba(255,255,255,0.1)"
                strokeDasharray="4 4"
              />
              <XAxis
                dataKey="label"
                stroke="#374151"
                tick={{ fill: "#4B5563", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                stroke="#374151"
                tick={{ fill: "#4B5563", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                unit="€"
                width={48}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="capital"
                stroke="#C8F000"
                strokeWidth={2}
                dot={<CustomDot />}
                activeDot={{ r: 4, fill: "#C8F000" }}
              />
            </LineChart>
          </ResponsiveContainer>

          <p className="text-xs text-muted-foreground text-center">
            Simulation avec mise constante de 10€ · Les résultats passés ne garantissent pas les résultats futurs.
          </p>
        </div>
      </div>
    </Section>
  );
}
