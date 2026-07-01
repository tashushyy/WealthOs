"use client";

/** Small shared UI building blocks for the dashboard. */

export function Card({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
      {children}
    </div>
  );
}

export function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-sm text-slate-400">{label}</span>
      <input
        type="number"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900/60 px-3 py-2 text-slate-100 outline-none focus:border-emerald-400"
      />
    </label>
  );
}

export function Stat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-semibold ${accent ? "text-emerald-400" : "text-slate-100"}`}>
        {value}
      </p>
    </div>
  );
}

export function SubmitButton({ loading, label }: { loading: boolean; label: string }) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full rounded-xl bg-emerald-500 py-2.5 font-medium text-slate-950 transition hover:bg-emerald-400 disabled:opacity-50"
    >
      {loading ? "Calculating…" : label}
    </button>
  );
}

export function ProgressBar({ fraction }: { fraction: number }) {
  const clamped = Math.max(0, Math.min(1, fraction));
  return (
    <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className="h-full rounded-full bg-emerald-500 transition-all"
        style={{ width: `${clamped * 100}%` }}
      />
    </div>
  );
}
