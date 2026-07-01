const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

export const compact = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export const percent = new Intl.NumberFormat("en-IN", {
  style: "percent",
  maximumFractionDigits: 1,
});

/** POST JSON to the backend and parse the result, surfacing engine errors. */
export async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(
      detail?.detail ? String(detail.detail) : `Request failed (${response.status})`,
    );
  }
  return (await response.json()) as T;
}

/** GET from the backend with query params, surfacing errors. */
export async function getJson<T>(path: string, params: Record<string, string>): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const response = await fetch(`${API_URL}${path}?${qs}`);
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new Error(
      detail?.detail ? String(detail.detail) : `Request failed (${response.status})`,
    );
  }
  return (await response.json()) as T;
}

// --- API response types ------------------------------------------------------

export type ProjectionResponse = {
  points: { year: number; contributed: number; value: number }[];
  final_value: number;
  total_contributed: number;
};

export type FireResponse = {
  fire_number: number;
  progress: number;
  years_to_fire: number | null;
};

export type SwpResponse = {
  survival_months: number | null;
  sustainable_monthly: number;
  points: { year: number; withdrawn: number; balance: number }[];
};

export type InstrumentResult = {
  id: string;
  name: string;
  kind: string;
  symbol: string | null;
};

export type QuoteResult = {
  id: string;
  name: string;
  price: number | null;
  expected_return: number | null;
  window_years: number | null;
  as_of: string | null;
};

export type PortfolioResponse = {
  total_invested: number;
  blended_return: number;
  blended_volatility: number | null;
  weights: { name: string; weight: number }[];
};

/** Human-readable months, e.g. 30 -> "2 yrs 6 mo". */
export function formatMonths(months: number | null): string {
  if (months === null) return "Outlasts the horizon";
  const years = Math.floor(months / 12);
  const rem = months % 12;
  const parts: string[] = [];
  if (years > 0) parts.push(`${years} yr${years === 1 ? "" : "s"}`);
  if (rem > 0) parts.push(`${rem} mo`);
  return parts.length > 0 ? parts.join(" ") : "0 mo";
}
