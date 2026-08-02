"use client";

import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { money, ms, percent } from "@/lib/formatters";
import type { LogRow } from "@/lib/types";
import { ActivityIcon, DatabaseIcon, PlugIcon, StopIcon, TraceIcon } from "@/components/ui/icons";

type Summary = {
  total_requests: number;
  average_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  error_rate: number;
  cancellation_rate: number;
  total_tokens: number;
  estimated_cost: number;
  success_rate: number;
  p50_ttft_ms: number;
  p95_ttft_ms: number;
  input_tokens: number;
  output_tokens: number;
  retry_count: number;
  fallback_count: number;
  replay_count: number;
  comparison_count: number;
  worker_processing_latency_ms: number;
  dead_letter_count: number;
  pii_redaction_count: number;
};

type ProviderRow = {
  label: string;
  requests: number;
  average_latency_ms: number;
  estimated_cost: number;
};

const chartText = "rgb(var(--color-ink) / 0.55)";
const chartGrid = "rgb(var(--color-ink) / 0.13)";
const teal = "rgb(var(--color-signal))";
const amber = "rgb(var(--color-amberline))";
const tooltipStyle = {
  backgroundColor: "rgb(var(--color-card) / 0.96)",
  border: "1px solid rgb(var(--color-signal) / 0.22)",
  borderRadius: "12px",
  boxShadow: "0 18px 42px -28px rgb(0 0 0 / 0.7), 0 0 24px rgb(var(--color-signal) / 0.12)",
  color: "rgb(var(--color-ink))"
};
const tooltipLabelStyle = { color: "rgb(var(--color-ink) / 0.72)", fontWeight: 600 };
const tooltipItemStyle = { color: teal };
const cursorStyle = { fill: "rgb(var(--color-signal) / 0.08)" };

export function DashboardView() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [latency, setLatency] = useState<Record<string, unknown>[]>([]);
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api<Summary>("/api/dashboard/summary"),
      api<Record<string, unknown>[]>("/api/dashboard/latency"),
      api<ProviderRow[]>("/api/dashboard/providers"),
      api<LogRow[]>("/api/logs")
    ])
      .then(([summaryData, latencyData, providerData, logData]) => {
        setSummary(summaryData);
        setLatency(latencyData);
        setProviders(providerData);
        setLogs(logData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, []);

  const statusData = useMemo(() => {
    const grouped = { completed: 0, error: 0, cancelled: 0 };
    logs.forEach((log) => {
      if (log.status in grouped) grouped[log.status as keyof typeof grouped] += 1;
    });
    return Object.entries(grouped).map(([status, count]) => ({ status, count }));
  }, [logs]);

  const tokenData = useMemo(() => {
    const grouped = new Map<string, number>();
    logs.forEach((log) => {
      const bucket = new Date(log.created_at).toISOString().slice(0, 10);
      grouped.set(bucket, (grouped.get(bucket) || 0) + log.total_tokens);
    });
    return [...grouped.entries()].sort().map(([bucket, value]) => ({ bucket, value }));
  }, [logs]);

  return (
    <main className="page-enter mx-auto max-w-7xl px-4 py-6">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-signal">Observability overview</p>
          <h1 className="mt-1 text-2xl font-semibold">Dashboard</h1>
          <p className="mt-1 text-sm text-ink/55">Latency, cost, usage, errors, and cancellation health from real inference logs.</p>
        </div>
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <MetricGroup title="Overall health">
        <Metric icon={<DatabaseIcon className="h-5 w-5" />} label="Total requests" value={summary?.total_requests ?? 0} hint="Gateway calls observed" tone="info" />
        <Metric icon={<ActivityIcon className="h-5 w-5" />} label="Success rate" value={percent(summary?.success_rate)} hint={`${Math.round((summary?.success_rate ?? 0) * (summary?.total_requests ?? 0))} of ${summary?.total_requests ?? 0} completed`} tone={(summary?.success_rate ?? 0) < 0.9 ? "warning" : "success"} />
        <Metric icon={<TraceIcon className="h-5 w-5" />} label="P95 latency" value={ms(summary?.p95_latency_ms)} hint="Tail request duration" tone={(summary?.p95_latency_ms ?? 0) > 1000 ? "danger" : "neutral"} />
        <Metric icon={<PlugIcon className="h-5 w-5" />} label="Estimated cost" value={money(summary?.estimated_cost ?? 0)} hint="Provider cost estimate" tone="neutral" />
      </MetricGroup>
      <MetricGroup title="Inference performance">
        <Metric icon={<ActivityIcon className="h-5 w-5" />} label="P50 latency" value={ms(summary?.p50_latency_ms)} hint="Median request duration" tone="neutral" />
        <Metric icon={<ActivityIcon className="h-5 w-5" />} label="P50 TTFT" value={ms(summary?.p50_ttft_ms)} hint="Median time to first token" tone="neutral" />
        <Metric icon={<ActivityIcon className="h-5 w-5" />} label="P95 TTFT" value={ms(summary?.p95_ttft_ms)} hint="Tail time to first token" tone="neutral" />
        <Metric icon={<DatabaseIcon className="h-5 w-5" />} label="Total tokens" value={summary?.total_tokens ?? 0} hint="Input plus output tokens" tone="info" />
      </MetricGroup>
      <MetricGroup title="Resilience">
        <Metric icon={<PlugIcon className="h-5 w-5" />} label="Retries" value={summary?.retry_count ?? 0} hint="Retry attempts" tone="info" />
        <Metric icon={<TraceIcon className="h-5 w-5" />} label="Fallbacks" value={summary?.fallback_count ?? 0} hint="Alternate provider routes" tone="info" />
        <Metric icon={<DatabaseIcon className="h-5 w-5" />} label="Dead letters" value={summary?.dead_letter_count ?? 0} hint="Worker messages requiring review" tone={(summary?.dead_letter_count ?? 0) ? "danger" : "success"} />
        <Metric icon={<ActivityIcon className="h-5 w-5" />} label="Error rate" value={percent(summary?.error_rate)} hint="Provider or request failures" tone={(summary?.error_rate ?? 0) > 0.1 ? "danger" : "success"} />
      </MetricGroup>
      <MetricGroup title="Product activity">
        <Metric icon={<TraceIcon className="h-5 w-5" />} label="Replays" value={summary?.replay_count ?? 0} hint="Linked replay traces" tone="neutral" />
        <Metric icon={<TraceIcon className="h-5 w-5" />} label="Comparisons" value={summary?.comparison_count ?? 0} hint="Comparison runs" tone="neutral" />
        <Metric icon={<StopIcon className="h-5 w-5" />} label="Cancellations" value={percent(summary?.cancellation_rate)} hint="User-stopped streams" tone={(summary?.cancellation_rate ?? 0) > 0 ? "warning" : "success"} />
        <Metric icon={<DatabaseIcon className="h-5 w-5" />} label="PII redactions" value={summary?.pii_redaction_count ?? 0} hint="Persisted redaction events" tone="info" />
      </MetricGroup>

      <div className="mt-6 grid gap-5 xl:grid-cols-2">
        <Chart title="Latency over time" subtitle="Average latency by day" empty={!latency.length}>
          <LineChart data={latency}>
            <CartesianGrid strokeDasharray="4 6" stroke={chartGrid} vertical={false} />
            <XAxis dataKey="bucket" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} width={44} />
            <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} cursor={{ stroke: teal, strokeOpacity: 0.28 }} />
            <Line type="monotone" dataKey="value" stroke={teal} strokeWidth={3} dot={{ r: 5, strokeWidth: 3, fill: "rgb(var(--color-card))", stroke: teal }} activeDot={{ r: 7, strokeWidth: 3, fill: teal, stroke: "rgb(var(--color-card))" }} />
          </LineChart>
        </Chart>
        <Chart title="Provider/model usage split" subtitle="Requests by configured target" empty={!providers.length}>
          <BarChart data={providers} barCategoryGap="32%">
            <CartesianGrid strokeDasharray="4 6" stroke={chartGrid} vertical={false} />
            <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} interval={0} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} allowDecimals={false} width={36} />
            <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={tooltipItemStyle} cursor={cursorStyle} />
            <Bar dataKey="requests" fill={teal} radius={[8, 8, 2, 2]} maxBarSize={78} />
          </BarChart>
        </Chart>
        <Chart title="Status distribution" subtitle="Completed, failed, and cancelled requests" empty={!logs.length}>
          <BarChart data={statusData} barCategoryGap="40%">
            <CartesianGrid strokeDasharray="4 6" stroke={chartGrid} vertical={false} />
            <XAxis dataKey="status" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} allowDecimals={false} width={36} />
            <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={{ color: amber }} cursor={{ fill: "rgb(var(--color-amberline) / 0.08)" }} />
            <Bar dataKey="count" fill={amber} radius={[8, 8, 2, 2]} maxBarSize={88} />
          </BarChart>
        </Chart>
        <Chart title="Token usage" subtitle="Daily token volume from logs" empty={!tokenData.length}>
          <LineChart data={tokenData}>
            <CartesianGrid strokeDasharray="4 6" stroke={chartGrid} vertical={false} />
            <XAxis dataKey="bucket" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: chartText }} width={44} />
            <Tooltip contentStyle={tooltipStyle} labelStyle={tooltipLabelStyle} itemStyle={{ color: amber }} cursor={{ stroke: amber, strokeOpacity: 0.3 }} />
            <Line type="monotone" dataKey="value" stroke={amber} strokeWidth={3} dot={{ r: 5, strokeWidth: 3, fill: "rgb(var(--color-card))", stroke: amber }} activeDot={{ r: 7, strokeWidth: 3, fill: amber, stroke: "rgb(var(--color-card))" }} />
          </LineChart>
        </Chart>
      </div>
    </main>
  );
}

function MetricGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6 first:mt-0">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink/55">{title}</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
  hint,
  tone
}: {
  icon: ReactElement;
  label: string;
  value: string | number;
  hint: string;
  tone: "success" | "warning" | "danger" | "info" | "neutral";
}) {
  return (
    <div className={`metric-card metric-${tone}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="metric-icon">{icon}</div>
        <div className="metric-label">{label}</div>
      </div>
      <div className="mt-4 text-3xl font-semibold tracking-normal">{value}</div>
      <div className="metric-hint">{hint}</div>
    </div>
  );
}

function Chart({ title, subtitle, empty, children }: { title: string; subtitle: string; empty: boolean; children: ReactElement }) {
  return (
    <section className="dashboard-chart-card">
      <div className="mb-4">
        <h2 className="font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-ink/50">{subtitle}</p>
      </div>
      <div className="h-80">
        {empty ? (
          <div className="grid h-full place-items-center rounded-xl border border-dashed border-black/10 bg-paper/60 p-6 text-center text-sm text-ink/55">
            No inference data yet. Send a chat message to populate this chart.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}
