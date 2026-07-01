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
  getJson,
  percent,
  postJson,
  type FireResponse,
  type InstrumentResult,
  type PortfolioResponse,
  type ProjectionResponse,
  type QuoteResult,
  type SwpResponse,
} from "./lib";

type Tab = "projection" | "fire" | "swp" | "portfolio";

const TABS: { id: Tab; label: string }[] = [
  { id: "projection", label: "Projection" },
  { id: "fire", label: "FIRE" },
  { id: "swp", label: "Withdrawals" },
  { id: "portfolio", label: "Portfolio" },
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
        {tab === "portfolio" && <PortfolioPanel />}
      </div>

      <HowToRead tab={tab} />
    </main>
  );
}

// --- How to read -------------------------------------------------------------

const GUIDES: Record<Tab, { title: string; items: [string, string][]; note: string }> = {
  projection: {
    title: "How to read the projection",
    items: [
      ["Orange line", `your projected portfolio value each year.`],
      [
        "Dashed line",
        `the total you have invested so far. The gap between the two lines is your growth.`,
      ],
      [
        "Final value / Invested / Gain",
        `what you end with, what you put in, and the returns earned on top.`,
      ],
      ["Annual step-up", `raises your monthly investment by that percentage every year.`],
    ],
    note: `Assumes the same return every year — real markets move around, so treat this as a smooth estimate, not a promise.`,
  },
  fire: {
    title: "How to read FIRE",
    items: [
      [
        "FIRE number",
        `the corpus where a safe withdrawal covers your yearly expenses — 25× expenses at a 4% rate.`,
      ],
      ["Progress bar", `how far your current corpus is toward that number.`],
      [
        "Years to FIRE",
        `how long until your corpus plus monthly investing reaches the target, at the return you entered.`,
      ],
      [
        `"Not on this path"`,
        `the target is not reached within 100 years at these inputs — raise the monthly amount or the return.`,
      ],
    ],
    note: `The 4% rate is a common rule of thumb; very long retirements may need a lower rate, i.e. a larger corpus.`,
  },
  swp: {
    title: "How to read withdrawals",
    items: [
      [
        "Money lasts",
        `how long the corpus can fund your withdrawals — or "outlasts the horizon" if it never runs out in the period.`,
      ],
      [
        "Sustainable / month",
        `the starting monthly withdrawal that would exactly empty the corpus over your horizon — a safe-withdrawal benchmark.`,
      ],
      ["Orange line", `the remaining balance over time; when it reaches zero, the money is gone.`],
      ["Inflation", `raises your withdrawal each year so spending keeps pace with prices.`],
    ],
    note: `"Money lasts" uses your actual withdrawal while "sustainable" is solved for the horizon, so the two can look inconsistent — that is expected. Tax is not modelled.`,
  },
  portfolio: {
    title: "How to read the portfolio",
    items: [
      [
        "Search & add",
        `find mutual funds, stocks, ETFs, or commodities and add them, or add a holding manually.`,
      ],
      [
        "Expected return",
        `for searched instruments this is the trailing CAGR (up to ~5 years) — past performance, not a forecast. Edit it to your own view.`,
      ],
      [
        "Blended return",
        `the amount-weighted average of your holdings' returns — your portfolio's expected return.`,
      ],
      ["Allocation", `each holding's share of the total. Weights always sum to 100%.`],
      [
        "Risk note",
        `shown only if every holding has a volatility. It is a weighted average, which overstates real risk — diversification lowers it, but that needs correlation data we do not model.`,
      ],
    ],
    note: `Live prices come from unofficial free sources (AMFI for funds, Yahoo for stocks) and can be delayed or occasionally unavailable — enter values manually if a lookup fails.`,
  },
};

function HowToRead({ tab }: { tab: Tab }) {
  const guide = GUIDES[tab];
  return (
    <details open className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
      <summary className="cursor-pointer select-none font-semibold text-white">
        {guide.title}
      </summary>
      <ul className="mt-4 space-y-2 text-sm text-neutral-300">
        {guide.items.map(([term, meaning]) => (
          <li key={term}>
            <span className="font-medium text-[#d97760]">{term}</span> — {meaning}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-neutral-500">Note: {guide.note}</p>
    </details>
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

// --- Portfolio ---------------------------------------------------------------

type Row = {
  key: string;
  id: string | null;
  name: string;
  kind: string;
  amount: string;
  returnPct: string;
};

function newKey(): string {
  return Math.random().toString(36).slice(2);
}

function PortfolioPanel() {
  const [rows, setRows] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<InstrumentResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [summary, setSummary] = useState<PortfolioResponse | null>(null);
  const [growth, setGrowth] = useState<ProjectionResponse | null>(null);
  const [sip, setSip] = useState("10000");
  const [years, setYears] = useState("15");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const total = rows.reduce((sum, r) => sum + (Number(r.amount) || 0), 0);

  async function onSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setError(null);
    try {
      setResults(await getJson<InstrumentResult[]>("/api/instruments/search", { q: query }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function addFromSearch(item: InstrumentResult) {
    let returnPct = "";
    try {
      const quote = await getJson<QuoteResult>("/api/instruments/quote", { id: item.id });
      if (quote.expected_return != null) returnPct = (quote.expected_return * 100).toFixed(1);
    } catch {
      // Leave the return blank for manual entry if the quote lookup fails.
    }
    setRows((prev) => [
      ...prev,
      { key: newKey(), id: item.id, name: item.name, kind: item.kind, amount: "100000", returnPct },
    ]);
    setResults([]);
    setQuery("");
  }

  function addManual() {
    setRows((prev) => [
      ...prev,
      { key: newKey(), id: null, name: "", kind: "manual", amount: "100000", returnPct: "12" },
    ]);
  }

  function updateRow(key: string, field: "name" | "amount" | "returnPct", value: string) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, [field]: value } : r)));
  }

  function removeRow(key: string) {
    setRows((prev) => prev.filter((r) => r.key !== key));
  }

  async function calculate() {
    setError(null);
    setLoading(true);
    setGrowth(null);
    try {
      const holdings = rows.map((r) => ({
        name: r.name.trim() || "Unnamed",
        amount: Number(r.amount) || 0,
        expected_return: (Number(r.returnPct) || 0) / 100,
      }));
      setSummary(await postJson<PortfolioResponse>("/api/portfolio", { holdings }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not calculate");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  async function projectGrowth() {
    if (!summary) return;
    try {
      setGrowth(
        await postJson<ProjectionResponse>("/api/projection", {
          principal: summary.total_invested,
          monthly_contribution: Number(sip) || 0,
          annual_return: summary.blended_return,
          years: Number(years) || 1,
          annual_step_up: 0,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Projection failed");
    }
  }

  return (
    <div className="space-y-8">
      <Card>
        <form onSubmit={onSearch} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search funds, stocks, gold…"
            className="flex-1 rounded-xl border border-white/10 bg-neutral-900/60 px-3 py-2 text-white outline-none focus:border-[#d97760]"
          />
          <button
            type="submit"
            disabled={searching}
            className="rounded-xl bg-[#d97760] px-4 font-medium text-black transition hover:bg-[#e08a76] disabled:opacity-50"
          >
            {searching ? "…" : "Search"}
          </button>
          <button
            type="button"
            onClick={addManual}
            className="rounded-xl border border-white/15 px-4 font-medium text-white transition hover:border-[#d97760]"
          >
            + Manual
          </button>
        </form>

        {results.length > 0 && (
          <ul className="mt-4 divide-y divide-white/5 rounded-xl border border-white/10">
            {results.map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm text-white">{item.name}</p>
                  <p className="text-xs text-neutral-500">{item.kind.replace("_", " ")}</p>
                </div>
                <button
                  onClick={() => addFromSearch(item)}
                  className="shrink-0 rounded-lg bg-white/10 px-3 py-1 text-sm text-white hover:bg-[#d97760] hover:text-black"
                >
                  Add
                </button>
              </li>
            ))}
          </ul>
        )}

        {rows.length > 0 ? (
          <div className="mt-6 space-y-2">
            <div className="grid grid-cols-[1fr_110px_90px_70px_32px] gap-2 px-1 text-xs uppercase tracking-wide text-neutral-500">
              <span>Holding</span>
              <span>Amount (₹)</span>
              <span>Return %</span>
              <span>Weight</span>
              <span />
            </div>
            {rows.map((r) => (
              <div key={r.key} className="grid grid-cols-[1fr_110px_90px_70px_32px] items-center gap-2">
                <input
                  value={r.name}
                  onChange={(e) => updateRow(r.key, "name", e.target.value)}
                  placeholder="Name"
                  className="rounded-lg border border-white/10 bg-neutral-900/60 px-2 py-1.5 text-sm text-white outline-none focus:border-[#d97760]"
                />
                <input
                  type="number"
                  value={r.amount}
                  onChange={(e) => updateRow(r.key, "amount", e.target.value)}
                  className="rounded-lg border border-white/10 bg-neutral-900/60 px-2 py-1.5 text-sm text-white outline-none focus:border-[#d97760]"
                />
                <input
                  type="number"
                  value={r.returnPct}
                  onChange={(e) => updateRow(r.key, "returnPct", e.target.value)}
                  className="rounded-lg border border-white/10 bg-neutral-900/60 px-2 py-1.5 text-sm text-white outline-none focus:border-[#d97760]"
                />
                <span className="text-sm text-neutral-400">
                  {total > 0 ? percent.format((Number(r.amount) || 0) / total) : "—"}
                </span>
                <button
                  onClick={() => removeRow(r.key)}
                  className="text-neutral-500 hover:text-[#d97760]"
                  aria-label="Remove"
                >
                  ×
                </button>
              </div>
            ))}
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm text-neutral-400">Total: {currency.format(total)}</span>
              <SubmitButtonInline loading={loading} onClick={calculate} />
            </div>
          </div>
        ) : (
          <p className="mt-6 text-sm text-neutral-500">
            Search for an instrument or add a manual holding to begin.
          </p>
        )}
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </Card>

      {summary && (
        <Card>
          <div className="grid grid-cols-3 gap-4">
            <Stat label="Blended return" value={percent.format(summary.blended_return)} accent />
            <Stat label="Total invested" value={currency.format(summary.total_invested)} />
            <Stat
              label="Est. volatility"
              value={
                summary.blended_volatility != null
                  ? percent.format(summary.blended_volatility)
                  : "—"
              }
            />
          </div>

          <div className="mt-6 space-y-3">
            <p className="text-sm text-neutral-400">Allocation</p>
            {summary.weights.map((w) => (
              <div key={w.name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-neutral-300">{w.name}</span>
                  <span className="text-neutral-400">{percent.format(w.weight)}</span>
                </div>
                <ProgressBar fraction={w.weight} />
              </div>
            ))}
          </div>

          {summary.blended_volatility == null && (
            <p className="mt-4 text-xs text-neutral-500">
              Add a volatility to every holding to see a blended risk estimate.
            </p>
          )}

          <div className="mt-8 border-t border-white/10 pt-6">
            <p className="text-sm text-neutral-400">
              Project growth at the blended {percent.format(summary.blended_return)} return
            </p>
            <div className="mt-3 flex flex-wrap items-end gap-3">
              <label className="text-sm text-neutral-400">
                Monthly SIP (₹)
                <input
                  type="number"
                  value={sip}
                  onChange={(e) => setSip(e.target.value)}
                  className="mt-1 block w-36 rounded-lg border border-white/10 bg-neutral-900/60 px-2 py-1.5 text-white outline-none focus:border-[#d97760]"
                />
              </label>
              <label className="text-sm text-neutral-400">
                Years
                <input
                  type="number"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                  className="mt-1 block w-24 rounded-lg border border-white/10 bg-neutral-900/60 px-2 py-1.5 text-white outline-none focus:border-[#d97760]"
                />
              </label>
              <button
                onClick={projectGrowth}
                className="rounded-xl bg-[#d97760] px-4 py-2 font-medium text-black transition hover:bg-[#e08a76]"
              >
                Project
              </button>
            </div>

            {growth && (
              <div className="mt-6 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={growth.points} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
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
                    <Line
                      type="monotone"
                      dataKey="value"
                      name="Portfolio value"
                      stroke="#d97760"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}

function SubmitButtonInline({ loading, onClick }: { loading: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="rounded-xl bg-[#d97760] px-5 py-2 font-medium text-black transition hover:bg-[#e08a76] disabled:opacity-50"
    >
      {loading ? "Calculating…" : "Calculate portfolio"}
    </button>
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
