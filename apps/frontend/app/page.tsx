"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, Field, ProgressBar, Stat, SubmitButton } from "./components";
import {
  compact,
  currency,
  formatMonths,
  percent,
  postJson,
  type FireResponse,
  type ProjectionResponse,
  type SwpResponse,
} from "./lib";

type Tab = "projection" | "fire" | "swp";

const TABS: { id: Tab; label: string }[] = [
  { id: "projection", label: "Projection" },
  { id: "fire", label: "FIRE" },
  { id: "swp", label: "Withdrawals" },
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("projection");

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex items-center gap-3">
        <svg
          width="44"
          height="44"
          viewBox="0 0 100 100"
          fill="none"
          strokeWidth={7}
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polygon points="50,10 68,28 50,46 32,28" stroke="#d97760" />
          <polygon points="50,54 68,72 50,90 32,72" stroke="#d97760" />
          <polygon points="28,32 46,50 28,68 10,50" stroke="#ffffff" />
          <polygon points="72,32 90,50 72,68 54,50" stroke="#ffffff" />
        </svg>
        <span className="font-serif text-3xl font-semibold tracking-wide">
          <span className="text-white">CODED</span>
          <span className="text-[#d97760]">MIND</span>
        </span>
      </div>
      <p className="mt-2 text-neutral-400">Plan your investments, independence, and withdrawals.</p>

      <div className="mt-6 flex gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition ${
              tab === t.id ? "bg-[#d97760] text-black" : "text-neutral-300 hover:text-white"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {tab === "projection" && <ProjectionPanel />}
        {tab === "fire" && <FirePanel />}
        {tab === "swp" && <SwpPanel />}
      </div>
    </main>
  );
}

// --- Projection --------------------------------------------------------------

function ProjectionPanel() {
  const [form, setForm] = useState({
    principal: "100000",
    monthlyContribution: "10000",
    annualReturnPct: "12",
    years: "20",
    stepUpPct: "10",
  });
  const [result, setResult] = useState<ProjectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await postJson<ProjectionResponse>("/api/projection", {
        principal: Number(form.principal),
        monthly_contribution: Number(form.monthlyContribution),
        annual_return: Number(form.annualReturnPct) / 100,
        years: Number(form.years),
        annual_step_up: Number(form.stepUpPct) / 100,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  const gain = result ? result.final_value - result.total_contributed : 0;

  return (
    <div className="grid gap-8 md:grid-cols-[320px_1fr]">
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Starting amount (₹)" value={form.principal} onChange={(v) => set("principal", v)} />
          <Field
            label="Monthly investment (₹)"
            value={form.monthlyContribution}
            onChange={(v) => set("monthlyContribution", v)}
          />
          <Field
            label="Expected return (% / yr)"
            value={form.annualReturnPct}
            onChange={(v) => set("annualReturnPct", v)}
          />
          <Field label="Years" value={form.years} onChange={(v) => set("years", v)} />
          <Field label="Annual step-up (%)" value={form.stepUpPct} onChange={(v) => set("stepUpPct", v)} />
          <SubmitButton loading={loading} label="Project" />
          {error && <p className="text-sm text-rose-400">{error}</p>}
        </form>
      </Card>

      <Card>
        {result ? (
          <>
            <div className="grid grid-cols-3 gap-4">
              <Stat label="Final value" value={currency.format(result.final_value)} />
              <Stat label="Invested" value={currency.format(result.total_contributed)} />
              <Stat label="Gain" value={currency.format(gain)} accent />
            </div>
            <div className="mt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={result.points} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
                  <XAxis dataKey="year" stroke="#94a3b8" tickLine={false} />
                  <YAxis
                    stroke="#94a3b8"
                    tickLine={false}
                    width={48}
                    tickFormatter={(v) => compact.format(v as number)}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v) => currency.format(v as number)}
                    labelFormatter={(label) => `Year ${label}`}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="value" name="Portfolio value" stroke="#d97760" strokeWidth={2} dot={false} />
                  <Line
                    type="monotone"
                    dataKey="contributed"
                    name="Invested"
                    stroke="#a3a3a3"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <Placeholder text="Enter your numbers and hit Project." />
        )}
      </Card>
    </div>
  );
}

// --- FIRE --------------------------------------------------------------------

function FirePanel() {
  const [form, setForm] = useState({
    annualExpenses: "600000",
    withdrawalPct: "4",
    currentCorpus: "2500000",
    monthlyContribution: "50000",
    annualReturnPct: "10",
  });
  const [result, setResult] = useState<FireResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await postJson<FireResponse>("/api/fire", {
        annual_expenses: Number(form.annualExpenses),
        withdrawal_rate: Number(form.withdrawalPct) / 100,
        current_corpus: Number(form.currentCorpus),
        monthly_contribution: Number(form.monthlyContribution),
        annual_return: Number(form.annualReturnPct) / 100,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-8 md:grid-cols-[320px_1fr]">
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Annual expenses (₹)" value={form.annualExpenses} onChange={(v) => set("annualExpenses", v)} />
          <Field label="Withdrawal rate (%)" value={form.withdrawalPct} onChange={(v) => set("withdrawalPct", v)} />
          <Field label="Current corpus (₹)" value={form.currentCorpus} onChange={(v) => set("currentCorpus", v)} />
          <Field
            label="Monthly investment (₹)"
            value={form.monthlyContribution}
            onChange={(v) => set("monthlyContribution", v)}
          />
          <Field
            label="Expected return (% / yr)"
            value={form.annualReturnPct}
            onChange={(v) => set("annualReturnPct", v)}
          />
          <SubmitButton loading={loading} label="Calculate FIRE" />
          {error && <p className="text-sm text-rose-400">{error}</p>}
        </form>
      </Card>

      <Card>
        {result ? (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <Stat label="FIRE number" value={currency.format(result.fire_number)} />
              <Stat
                label="Years to FIRE"
                value={result.years_to_fire === null ? "Not on this path" : `${result.years_to_fire} yrs`}
                accent
              />
            </div>
            <div>
              <div className="mb-2 flex justify-between text-sm text-neutral-400">
                <span>Progress</span>
                <span>{percent.format(result.progress)}</span>
              </div>
              <ProgressBar fraction={result.progress} />
            </div>
            {result.years_to_fire === null && (
              <p className="text-sm text-neutral-400">
                At the current contribution and return, the corpus does not reach the target within
                100 years. Try a higher monthly investment or return.
              </p>
            )}
          </div>
        ) : (
          <Placeholder text="Enter your numbers and hit Calculate." />
        )}
      </Card>
    </div>
  );
}

// --- SWP ---------------------------------------------------------------------

function SwpPanel() {
  const [form, setForm] = useState({
    corpus: "10000000",
    monthlyWithdrawal: "50000",
    annualReturnPct: "8",
    inflationPct: "6",
    years: "30",
  });
  const [result, setResult] = useState<SwpResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function set(field: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await postJson<SwpResponse>("/api/swp", {
        corpus: Number(form.corpus),
        monthly_withdrawal: Number(form.monthlyWithdrawal),
        annual_return: Number(form.annualReturnPct) / 100,
        annual_inflation: Number(form.inflationPct) / 100,
        years: Number(form.years),
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-8 md:grid-cols-[320px_1fr]">
      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label="Corpus (₹)" value={form.corpus} onChange={(v) => set("corpus", v)} />
          <Field
            label="Monthly withdrawal (₹)"
            value={form.monthlyWithdrawal}
            onChange={(v) => set("monthlyWithdrawal", v)}
          />
          <Field
            label="Expected return (% / yr)"
            value={form.annualReturnPct}
            onChange={(v) => set("annualReturnPct", v)}
          />
          <Field label="Inflation (% / yr)" value={form.inflationPct} onChange={(v) => set("inflationPct", v)} />
          <Field label="Horizon (years)" value={form.years} onChange={(v) => set("years", v)} />
          <SubmitButton loading={loading} label="Simulate" />
          {error && <p className="text-sm text-rose-400">{error}</p>}
        </form>
      </Card>

      <Card>
        {result ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Stat label="Money lasts" value={formatMonths(result.survival_months)} />
              <Stat
                label="Sustainable / month"
                value={currency.format(result.sustainable_monthly)}
                accent
              />
            </div>
            <div className="mt-6 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={result.points} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff14" />
                  <XAxis dataKey="year" stroke="#94a3b8" tickLine={false} />
                  <YAxis
                    stroke="#94a3b8"
                    tickLine={false}
                    width={48}
                    tickFormatter={(v) => compact.format(v as number)}
                  />
                  <Tooltip
                    contentStyle={tooltipStyle}
                    formatter={(v) => currency.format(v as number)}
                    labelFormatter={(label) => `Year ${label}`}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="balance" name="Balance" stroke="#d97760" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <Placeholder text="Enter your numbers and hit Simulate." />
        )}
      </Card>
    </div>
  );
}

// --- shared ------------------------------------------------------------------

const tooltipStyle = {
  background: "#171717",
  border: "1px solid #ffffff1a",
  borderRadius: 12,
  color: "#ffffff",
} as const;

function Placeholder({ text }: { text: string }) {
  return (
    <div className="flex h-full min-h-72 items-center justify-center text-neutral-500">{text}</div>
  );
}
