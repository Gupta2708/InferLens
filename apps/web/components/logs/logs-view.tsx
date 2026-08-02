"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { compactDate, money, ms, shortTraceId } from "@/lib/formatters";
import type { LogRow, ProviderCatalog } from "@/lib/types";
import { Badge, ModelChip, ProviderChip, StatusChip } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CopyIcon, DatabaseIcon, TraceIcon } from "@/components/ui/icons";

export function LogsView() {
  const [logs, setLogs] = useState<LogRow[]>([]);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [status, setStatus] = useState("");
  const [conversationId, setConversationId] = useState("");
  const [traceId, setTraceId] = useState("");
  const [errorType, setErrorType] = useState("");
  const [latencyGt, setLatencyGt] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState("");
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);

  useEffect(() => {
    api<ProviderCatalog>("/api/providers").then(setCatalog).catch(() => undefined);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (provider) params.set("provider", provider);
    if (model) params.set("model", model);
    if (status) params.set("status", status);
    if (conversationId) params.set("conversation_id", conversationId);
    if (traceId) params.set("trace_id", traceId);
    if (errorType) params.set("error_type", errorType);
    if (latencyGt) params.set("latency_gt", latencyGt);
    if (dateFrom) params.set("date_from", new Date(dateFrom).toISOString());
    if (dateTo) params.set("date_to", new Date(dateTo).toISOString());
    api<LogRow[]>(`/api/logs?${params.toString()}`)
      .then((rows) => {
        setLogs(rows);
        setError("");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load logs"));
  }, [provider, model, status, conversationId, traceId, errorType, latencyGt, dateFrom, dateTo]);

  function clearFilters() {
    setProvider("");
    setModel("");
    setStatus("");
    setConversationId("");
    setTraceId("");
    setErrorType("");
    setLatencyGt("");
    setDateFrom("");
    setDateTo("");
  }

  const hasFilters = Boolean(provider || model || status || conversationId || traceId || errorType || latencyGt || dateFrom || dateTo);
  const providers = useMemo(() => [...new Set(catalog?.models.filter((item) => item.enabled).map((item) => item.provider) || [])], [catalog]);
  const models = useMemo(() => (catalog?.models || []).filter((item) => !provider || item.provider === provider), [catalog, provider]);
  const errorCategories = useMemo(() => [...new Set(logs.map((row) => row.error_type).filter(Boolean))] as string[], [logs]);

  return (
    <main className="page-enter mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-signal">Inference ledger</p>
          <h1 className="mt-1 text-2xl font-semibold">Inference Logs</h1>
          <p className="mt-1 text-sm text-ink/55">Filter gateway calls by provider, status, latency, conversation, and date range.</p>
        </div>
        <Button onClick={clearFilters} disabled={!hasFilters} variant="secondary">
          Clear filters
        </Button>
      </div>

      <section className="surface-card mb-5 p-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <FilterSelect label="Provider" value={provider} onChange={(value) => { setProvider(value); setModel(""); }} options={providers} allLabel="all providers" />
          <FilterSelect label="Model" value={model} onChange={setModel} options={models.map((item) => item.model)} allLabel="all models" />
          <label className="grid gap-1 text-xs font-medium uppercase text-ink/50">
            Status
            <select className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-signal focus:outline-none" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">all statuses</option>
              <option value="completed">completed</option>
              <option value="error">error</option>
              <option value="cancelled">cancelled</option>
            </select>
          </label>
          <FilterInput label="Conversation ID" placeholder="e.g. UUID" value={conversationId} onChange={setConversationId} />
          <FilterInput label="Trace ID" placeholder="e.g. trace_abc123" value={traceId} onChange={setTraceId} />
          <FilterSelect label="Error category" value={errorType} onChange={setErrorType} options={errorCategories} allLabel="all error categories" />
          <FilterInput label="Latency greater than" placeholder="ms" value={latencyGt} onChange={setLatencyGt} />
          <FilterInput label="From" type="date" value={dateFrom} onChange={setDateFrom} />
          <FilterInput label="To" type="date" value={dateTo} onChange={setDateTo} />
        </div>
      </section>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <div className="surface-card overflow-hidden">
        <div className="flex items-center justify-between border-b border-black/10 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <DatabaseIcon className="h-5 w-5 text-signal" />
            {logs.length} log rows
          </div>
          <p className="text-xs text-ink/45">Trace previews are redacted by default.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1040px] border-collapse text-sm">
            <thead className="sticky top-0 z-10 bg-paper text-left text-xs uppercase text-ink/55 shadow-sm">
              <tr>
                <th className="p-3">Time</th>
                <th className="p-3">Status</th>
                <th className="p-3">Provider</th>
                <th className="p-3">Model</th>
                <th className="p-3">Latency</th>
                <th className="p-3">TTFT</th>
                <th className="p-3">Tokens</th>
                <th className="p-3">Cost</th>
                <th className="p-3">Error</th>
                <th className="p-3">Trace ID</th>
                <th className="sticky right-0 bg-paper p-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.trace_id} className="border-t border-black/5 transition hover:bg-paper/70">
                  <td className="whitespace-nowrap p-3">{compactDate(log.created_at)}</td>
                  <td className="p-3"><StatusChip status={log.status} /></td>
                  <td className="p-3"><ProviderChip provider={log.provider} /></td>
                  <td className="p-3"><ModelChip model={log.model} /></td>
                  <td className="whitespace-nowrap p-3">{ms(log.latency_ms)}</td>
                  <td className="whitespace-nowrap p-3">{log.time_to_first_token_ms == null ? "Not measured" : ms(log.time_to_first_token_ms)}</td>
                  <td className="p-3">{log.total_tokens}</td>
                  <td className="whitespace-nowrap p-3">{money(log.estimated_total_cost)}</td>
                  <td className="p-3">{log.error_type ? <Badge tone="error">{log.error_type}</Badge> : <span className="text-ink/40">-</span>}</td>
                  <td className="p-3 font-mono text-xs" title={log.trace_id}>{shortTraceId(log.trace_id)}</td>
                  <td className="sticky right-0 bg-white p-3 shadow-[-10px_0_16px_-18px_rgba(0,0,0,0.4)]">
                    <div className="flex items-center gap-2">
                      <button
                        title="Copy trace ID"
                        onClick={() => navigator.clipboard?.writeText(log.trace_id)}
                        className="focus-ring inline-grid h-8 w-8 place-items-center rounded-md border border-black/10 text-ink/55 transition hover:text-signal"
                      >
                        <CopyIcon className="h-4 w-4" />
                      </button>
                      <Link className="inline-flex items-center gap-1 rounded-md border border-signal/20 bg-signal/10 px-2 py-1.5 text-xs font-medium text-signal transition hover:bg-signal/15" href={`/traces/${log.trace_id}`}>
                        <TraceIcon className="h-3.5 w-3.5" />
                        Trace
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!logs.length && (
            <div className="grid min-h-64 place-items-center p-8 text-center text-sm text-ink/55">
              No inference logs yet. Send a chat message or run a provider comparison.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

function FilterSelect({ label, value, onChange, options, allLabel }: { label: string; value: string; onChange: (value: string) => void; options: string[]; allLabel: string }) {
  return <label className="grid gap-1 text-xs font-medium uppercase text-ink/50">{label}<select className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-signal focus:outline-none" value={value} onChange={(event) => onChange(event.target.value)}><option value="">{allLabel}</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function FilterInput({
  label,
  value,
  onChange,
  placeholder,
  type = "text"
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="grid gap-1 text-xs font-medium uppercase text-ink/50">
      {label}
      <input
        className="rounded-lg border border-black/15 bg-white px-3 py-2 text-sm text-ink shadow-sm transition placeholder:text-ink/35 focus:border-signal focus:outline-none"
        placeholder={placeholder}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
