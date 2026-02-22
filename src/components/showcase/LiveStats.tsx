"use client";

import { useEffect, useState } from "react";

interface ShowcaseStats {
  products: number;
  categories: number;
  warehouses: number;
  stock_alerts: number;
  stock_transfers: number;
  audit_log_entries: number;
}

interface StatCardProps {
  label: string;
  value: number | null;
  colorClass: string;
}

function StatCard({ label, value, colorClass }: StatCardProps) {
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (value === null) return;
    if (value === 0) {
      setDisplayed(0);
      return;
    }
    const duration = 800;
    const steps = 40;
    const step = value / steps;
    let current = 0;
    const interval = setInterval(() => {
      current += step;
      if (current >= value) {
        setDisplayed(value);
        clearInterval(interval);
      } else {
        setDisplayed(Math.floor(current));
      }
    }, duration / steps);
    return () => clearInterval(interval);
  }, [value]);

  const isLoading = value === null;

  return (
    <div className="stat-card bg-gray-900 border border-gray-800 rounded-xl p-5 text-center transition-all duration-200 hover:-translate-y-0.5">
      <div
        className={`text-3xl font-bold tabular-nums ${colorClass}${isLoading ? " animate-pulse" : ""}`}
        aria-live="polite"
        aria-label={isLoading ? `${label}: loading` : `${label}: ${value?.toLocaleString()}`}
      >
        {isLoading ? "—" : displayed.toLocaleString()}
      </div>
      <div className="text-xs text-gray-500 mt-2 uppercase tracking-wider">{label}</div>
    </div>
  );
}

interface LiveStatsProps {
  statsUrl?: string;
  className?: string;
}

export function LiveStats({
  statsUrl = "/api/v1/showcase/stats",
  className,
}: LiveStatsProps) {
  const [stats, setStats] = useState<ShowcaseStats | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchStats() {
      try {
        const res = await fetch(statsUrl);
        if (!res.ok) throw new Error("non-ok");
        const data: ShowcaseStats = await res.json();
        if (!cancelled) {
          setStats(data);
          setLastUpdated(new Date().toLocaleTimeString());
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    }

    fetchStats();
    return () => {
      cancelled = true;
    };
  }, [statsUrl]);

  const statItems = [
    { label: "Products", key: "products" as const, colorClass: "text-blue-400" },
    { label: "Categories", key: "categories" as const, colorClass: "text-purple-400" },
    { label: "Warehouses", key: "warehouses" as const, colorClass: "text-emerald-400" },
    { label: "Stock Alerts", key: "stock_alerts" as const, colorClass: "text-amber-400" },
    { label: "Transfers", key: "stock_transfers" as const, colorClass: "text-cyan-400" },
    { label: "Audit Entries", key: "audit_log_entries" as const, colorClass: "text-rose-400" },
  ];

  return (
    <section
      className={`max-w-7xl mx-auto px-4 sm:px-6 py-16${className ? ` ${className}` : ""}`}
      aria-labelledby="stats-heading"
    >
      <div className="text-center mb-10">
        <h2 id="stats-heading" className="text-2xl sm:text-3xl font-bold text-white mb-2">
          Live Stats
        </h2>
        <p className="text-gray-500 text-sm">
          Real-time data from{" "}
          <code className="bg-gray-800 px-1.5 py-0.5 rounded text-gray-300 text-xs">
            {statsUrl}
          </code>
        </p>
      </div>

      <div
        className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4"
        role="region"
        aria-label="Live statistics"
      >
        {statItems.map(({ label, key, colorClass }) => (
          <StatCard
            key={key}
            label={label}
            value={stats ? stats[key] : null}
            colorClass={colorClass}
          />
        ))}
      </div>

      <div className="text-center mt-4" aria-live="polite">
        {error && (
          <span className="text-xs text-red-500/70">
            Could not load stats — showing placeholder data
          </span>
        )}
        {lastUpdated && !error && (
          <span className="text-xs text-gray-600">Last updated: {lastUpdated}</span>
        )}
      </div>
    </section>
  );
}
