"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { getDefaultModelForProvider, getModelsForProvider } from "@/lib/providers";
import type { ProviderCatalog, ProviderModel } from "@/lib/types";
import { compactDate, money, ms, shortTraceId } from "@/lib/formatters";
import { Badge, ModelChip, ProviderChip, StatusChip } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CopyIcon, PlayIcon, SparkIcon, StopIcon, TraceIcon } from "@/components/ui/icons";

type Trace = {
  trace_id: string;
  status: string;
  conversation_id?: string | null;
  message_id?: string | null;
  summary: Record<string, any>;
  spans: Record<string, any>[];
  stream_events: Record<string, any>[];
  errors: Record<string, any>[];
  redactions: Record<string, any>[];
  replays: Record<string, any>[];
  otel?: Record<string, any>;
  external_trace_url?: string | null;
};

export function TraceView() {
  const params = useParams<{ traceId: string }>();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [replay, setReplay] = useState<Record<string, any> | null>(null);
  const [mockScenario, setMockScenario] = useState("");
  const [replayProvider, setReplayProvider] = useState("");
  const [replayModel, setReplayModel] = useState("");
  const [replacementPrompt, setReplacementPrompt] = useState("");
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [loadingReplay, setLoadingReplay] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    setTrace(await api<Trace>(`/api/traces/${params.traceId}`));
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load trace"));
    api<ProviderCatalog>("/api/providers").then((catalog) => setModels(catalog.models.filter((item) => item.enabled))).catch(() => undefined);
  }, [params.traceId]);

  async function runReplay(label: string, body: Record<string, unknown>) {
    setLoadingReplay(label);
    setError("");
    setNotice("");
    try {
      const result = await api<Record<string, any>>(`/api/traces/${params.traceId}/replay`, {
        method: "POST",
        body: JSON.stringify(body)
      });
      setReplay(result);
      setNotice(`${label} created ${result.status} replay ${result.trace_id}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replay failed");
    } finally {
      setLoadingReplay("");
    }
  }

  if (!trace) return <main className="mx-auto max-w-7xl px-4 py-6 text-sm text-ink/60">Loading trace...</main>;
  const summary = trace.summary || {};
  const replayModels = getModelsForProvider(models, replayProvider);

  return (
    <main className="page-enter mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium uppercase tracking-wide text-signal">Trace detail</p>
          <h1 className="mt-1 break-all text-2xl font-semibold">{trace.trace_id}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/60">
            A trace shows the full lifecycle of one LLM request, from message creation to provider call,
            stream events, logging, and worker persistence.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => navigator.clipboard?.writeText(trace.trace_id)}
            className="focus-ring inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-medium text-ink/70 transition hover:bg-paper hover:text-ink"
          >
            <CopyIcon className="h-4 w-4" />
            Copy trace ID
          </button>
          {trace.otel?.trace_id && <button onClick={() => navigator.clipboard?.writeText(String(trace.otel?.trace_id))} className="focus-ring inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-medium text-ink/70">Copy OTEL ID</button>}
          {trace.external_trace_url && <a className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-medium text-ink/70" href={trace.external_trace_url} target="_blank" rel="noreferrer">Open in external observability</a>}
          <Link className="inline-flex items-center gap-2 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-medium text-ink/70 transition hover:bg-paper hover:text-ink" href="/logs">
            Back to logs
          </Link>
        </div>
      </div>

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {notice && <div className="mb-4 rounded-xl border border-signal/20 bg-signal/10 p-4 text-sm text-signal">{notice}</div>}

      <section className="surface-card grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryMetric label="Status" value={<StatusChip status={trace.status} />} />
        <SummaryMetric label="Provider" value={<ProviderChip provider={summary.provider} />} />
        <SummaryMetric label="Model" value={<ModelChip model={summary.model} />} />
        <SummaryMetric label="Latency" value={ms(summary.latency_ms)} />
        <SummaryMetric label="First token" value={ms(summary.time_to_first_token_ms)} />
        <SummaryMetric label="Tokens" value={summary.tokens || 0} />
        <SummaryMetric label="Cost" value={money(summary.cost || 0)} />
        <SummaryMetric label={summary.error_type ? "Error" : "Message"} value={summary.error_type || (trace.message_id ? shortTraceId(String(trace.message_id)) : "-")} />
      </section>

      <section className="surface-card mt-5 grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryMetric label="OTEL trace" value={trace.otel?.trace_id ? shortTraceId(String(trace.otel.trace_id)) : "Not instrumented"} />
        <SummaryMetric label="Retries" value={summary.retry_count || 0} />
        <SummaryMetric label="Fallback" value={summary.fallback_provider || "None"} />
        <SummaryMetric label="Privacy" value={summary.content_captured ? "Redacted capture" : "Metadata only"} />
      </section>

      <Routing rows={summary.routing_history || []} />

      <section className="mt-5 grid gap-4 lg:grid-cols-2">
        <PreviewPanel title="Redacted input preview" value={summary.input_preview || ""} />
        <PreviewPanel title="Redacted output preview" value={summary.output_preview || ""} />
      </section>

      <section className="surface-card mt-5 p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="font-semibold">Replay</h2>
            <p className="mt-1 text-sm text-ink/50">Run controlled replays from the stored safe request snapshot.</p>
          </div>
          {replay && (
            <Link className="inline-flex items-center gap-2 rounded-full border border-signal/20 bg-signal/10 px-3 py-1.5 text-sm font-medium text-signal" href={`/traces/${replay.trace_id}`}>
              <TraceIcon className="h-4 w-4" />
              Open latest replay
            </Link>
          )}
        </div>
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(180px,0.7fr)_minmax(220px,0.9fr)_auto]">
          {!summary.content_captured && <label className="grid gap-1 text-xs font-medium uppercase text-ink/50 lg:col-span-4">Replacement prompt required for this replay<textarea value={replacementPrompt} onChange={(event) => setReplacementPrompt(event.target.value)} className="min-h-20 rounded-md border border-black/15 bg-white px-3 py-2 text-sm normal-case shadow-sm focus:border-signal focus:outline-none" placeholder="Enter the prompt to replay. The original content was not retained." /></label>}
          <select aria-label="Replay provider" value={replayProvider} onChange={(event) => { const next = event.target.value; setReplayProvider(next); setReplayModel(getDefaultModelForProvider(models, next)); }} className="rounded-md border border-black/15 bg-white px-3 py-2 text-sm shadow-sm focus:border-signal focus:outline-none">
            <option value="">Original provider ({summary.provider || "unknown"})</option>
            {[...new Set(models.map((item) => item.provider))].map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <select aria-label="Replay model" value={replayModel} onChange={(event) => setReplayModel(event.target.value)} disabled={!replayProvider} className="rounded-md border border-black/15 bg-white px-3 py-2 text-sm shadow-sm focus:border-signal focus:outline-none disabled:opacity-50">
            <option value="">Original model ({summary.model || "unknown"})</option>
            {replayModels.map((item) => <option key={item.model} value={item.model}>{item.model}</option>)}
          </select>
          <ReplayButton label="Create replay" loading={loadingReplay} disabled={!summary.content_captured && !replacementPrompt.trim()} onClick={() => runReplay("Create replay", { provider: replayProvider || undefined, model: replayModel || undefined, edited_user_message: replacementPrompt.trim() || undefined })} />
        </div>
        <details className="mt-3 text-sm text-ink/55"><summary className="cursor-pointer font-medium text-signal">Advanced replay options</summary><div className="mt-3 flex flex-wrap gap-2"><ReplayButton label="Lower temperature" loading={loadingReplay} onClick={() => runReplay("Lower temperature", { temperature: 0.2, edited_user_message: replacementPrompt.trim() || undefined })} /><ReplayButton label="No context" loading={loadingReplay} onClick={() => runReplay("No context", { without_context: true, edited_user_message: replacementPrompt.trim() || undefined })} /><input className="rounded-md border border-black/15 px-3 py-2 text-sm shadow-sm focus:border-signal focus:outline-none" placeholder="Mock scenario (optional)" value={mockScenario} onChange={(e) => setMockScenario(e.target.value)} /></div></details>
        <div className="mt-4 grid gap-3 rounded-xl border border-black/10 bg-paper/60 p-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <SummaryMetric label="Replay source" value={`${summary.provider || "-"} / ${summary.model || "-"}`} />
          <SummaryMetric label="Replay privacy" value={summary.content_captured ? "Exact replay snapshot available" : "Redacted replay or replacement prompt required"} />
          {replay && <>
            <SummaryMetric label="Replay target" value={`${replay.replay?.provider || "-"} / ${replay.replay?.model || "-"}`} />
            <SummaryMetric label="Status" value={`${replay.original?.status || "-"} → ${replay.replay?.status || replay.status || "-"}`} />
            <SummaryMetric label="Latency" value={`${ms(replay.original?.latency_ms)} → ${ms(replay.replay?.latency_ms)}`} />
            <SummaryMetric label="TTFT" value={`${ms(replay.original?.time_to_first_token_ms)} → ${ms(replay.replay?.time_to_first_token_ms)}`} />
            <SummaryMetric label="Tokens" value={`${(replay.original?.input_tokens || 0) + (replay.original?.output_tokens || 0)} → ${(replay.replay?.input_tokens || 0) + (replay.replay?.output_tokens || 0)}`} />
            <SummaryMetric label="Estimated cost" value={`${money(replay.original?.estimated_cost || 0)} → ${money(replay.replay?.estimated_cost || 0)}`} />
          </>}
        </div>
      </section>

      <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <Timeline rows={trace.spans} />
        <aside className="grid gap-5">
          <Redactions rows={trace.redactions} />
          <StreamEvents rows={trace.stream_events} />
          <ReplayHistory rows={trace.replays} />
          <Errors rows={trace.errors} />
        </aside>
      </div>
    </main>
  );
}

function SummaryMetric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase text-ink/45">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}

function PreviewPanel({ title, value }: { title: string; value: string }) {
  return (
    <section className="surface-card p-5">
      <h2 className="font-semibold">{title}</h2>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-paper p-4 text-xs leading-6 text-ink/80">
        {value || "No preview captured."}
      </pre>
    </section>
  );
}

function ReplayButton({ label, loading, onClick, disabled = false }: { label: string; loading: string; onClick: () => void; disabled?: boolean }) {
  const active = loading === label;
  return (
    <Button onClick={onClick} disabled={Boolean(loading) || disabled} variant="secondary">
      {active ? <StopIcon className="h-4 w-4" /> : <PlayIcon className="h-4 w-4" />}
      {active ? "Running" : label}
    </Button>
  );
}

function Routing({ rows }: { rows: Record<string, any>[] }) {
  return <section className="surface-card mt-5 p-5"><h2 className="font-semibold">Routing</h2><p className="mt-1 text-sm text-ink/50">Provider attempts, retries, fallback, and circuit-breaker activity.</p><div className="mt-3 space-y-2">{rows.map((row, index) => <div key={index} className="rounded-lg bg-paper p-3 text-sm">{row.provider} · attempt {row.attempt} · {row.outcome}{row.error_category ? ` · ${row.error_category}` : ""}{row.circuit_state ? ` · breaker ${row.circuit_state}` : ""}</div>)}{!rows.length && <EmptySmall>Primary provider completed without recorded retries.</EmptySmall>}</div></section>;
}

function Timeline({ rows }: { rows: Record<string, any>[] }) {
  return (
    <section className="surface-card p-5">
      <h2 className="font-semibold">Timeline</h2>
      <p className="mt-1 text-sm text-ink/50">Gateway and ingestion spans in execution order.</p>
      <div className="mt-5 space-y-4 border-l-2 border-signal/20 pl-5">
        {rows.map((row, index) => (
          <div key={`${row.span_id || row.name}-${index}`} className="relative rounded-xl border border-black/10 bg-white p-4 shadow-sm">
            <span className="absolute -left-[30px] top-5 h-3 w-3 rounded-full border-2 border-white bg-signal shadow" />
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{row.name || "span"}</h3>
                <p className="mt-1 text-xs text-ink/45">{compactDate(row.start_time)} - {row.end_time ? compactDate(row.end_time) : "open"}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusChip status={row.status || "ok"} />
                <Badge>{ms(row.duration_ms)}</Badge>
              </div>
            </div>
            {row.metadata_json && Object.keys(row.metadata_json).length > 0 && (
              <div className="mt-3 rounded-lg bg-paper p-3 text-xs text-ink/70">
                {Object.entries(row.metadata_json).slice(0, 5).map(([key, value]) => (
                  <div key={key} className="flex gap-2">
                    <span className="font-medium">{key}:</span>
                    <span className="truncate">{String(value)}</span>
                  </div>
                ))}
              </div>
            )}
            <details className="mt-3 text-xs">
              <summary className="cursor-pointer text-signal">Show raw span JSON</summary>
              <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-[#101817] p-3 text-[#e5eeea]">{JSON.stringify(row, null, 2)}</pre>
            </details>
          </div>
        ))}
        {!rows.length && <div className="text-sm text-ink/55">No spans recorded for this trace.</div>}
      </div>
    </section>
  );
}

function Redactions({ rows }: { rows: Record<string, any>[] }) {
  return (
    <InfoCard title="PII redactions" subtitle="Sensitive values redacted before observability persistence.">
      <div className="space-y-2">
        {rows.map((row, index) => (
          <div key={index} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm">
            <div className="font-medium">{row.field_name}</div>
            <div className="mt-1 text-xs text-ink/60">{row.pii_type} redacted {row.redacted_count} time(s)</div>
          </div>
        ))}
        {!rows.length && <EmptySmall>No PII redactions recorded.</EmptySmall>}
      </div>
    </InfoCard>
  );
}

function StreamEvents({ rows }: { rows: Record<string, any>[] }) {
  const firstEvents = rows.slice(0, 3);
  return (
    <InfoCard title="Stream events" subtitle={`${rows.length} event${rows.length === 1 ? "" : "s"} captured`}>
      <div className="mb-3 space-y-2">
        {firstEvents.map((row, index) => (
          <div key={index} className="rounded-lg bg-paper p-3 text-xs">
            <span className="font-medium">{row.sequence_number}. {row.event_type}</span>
            {row.delta_text && <span className="ml-2 text-ink/55">{String(row.delta_text).slice(0, 80)}</span>}
          </div>
        ))}
        {!firstEvents.length && <EmptySmall>No stream events recorded.</EmptySmall>}
      </div>
      <details>
        <summary className="cursor-pointer text-sm font-medium text-signal">Show stream event list</summary>
        <div className="mt-3 max-h-72 space-y-2 overflow-auto">
          {rows.map((row, index) => (
            <div key={index} className="rounded-lg bg-paper p-3 text-xs">
              <div className="font-medium">{row.sequence_number}. {row.event_type}</div>
              {row.delta_text && <div className="mt-1 whitespace-pre-wrap text-ink/60">{row.delta_text}</div>}
            </div>
          ))}
          {!rows.length && <EmptySmall>No stream events recorded.</EmptySmall>}
        </div>
      </details>
    </InfoCard>
  );
}

function ReplayHistory({ rows }: { rows: Record<string, any>[] }) {
  return (
    <InfoCard title="Replay history" subtitle="Linked traces created from this request.">
      <div className="space-y-2">
        {rows.map((row, index) => (
          <Link key={index} href={`/traces/${row.trace_id}`} className="block rounded-xl border border-black/10 bg-white p-3 text-sm transition hover:bg-paper">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-xs">{shortTraceId(row.trace_id)}</span>
              <StatusChip status={row.status} />
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-ink/55">
              <span>{row.provider || "-"}/{row.model || "-"}</span>
              <span>{ms(row.latency_ms)}</span>
              <span className="col-span-2">{compactDate(row.created_at)}</span>
            </div>
            <div className="mt-2 text-xs font-medium text-signal">Open trace</div>
          </Link>
        ))}
        {!rows.length && <EmptySmall>No replays yet.</EmptySmall>}
      </div>
    </InfoCard>
  );
}

function Errors({ rows }: { rows: Record<string, any>[] }) {
  return (
    <InfoCard title="Provider errors" subtitle="Normalized provider failures.">
      <div className="space-y-2">
        {rows.map((row, index) => (
          <div key={index} className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <div className="font-medium">{row.error_type}</div>
            <div className="mt-1 text-xs">{row.error_message}</div>
          </div>
        ))}
        {!rows.length && <EmptySmall>No provider errors recorded.</EmptySmall>}
      </div>
    </InfoCard>
  );
}

function InfoCard({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <section className="surface-card p-5">
      <h2 className="font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-ink/50">{subtitle}</p>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function EmptySmall({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-dashed border-black/10 bg-paper/60 p-4 text-sm text-ink/55">{children}</div>;
}
