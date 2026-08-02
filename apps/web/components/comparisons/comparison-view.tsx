"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { money, ms } from "@/lib/formatters";
import { getDefaultModelForProvider, getModelsForProvider } from "@/lib/providers";
import type { ProviderCatalog, ProviderModel } from "@/lib/types";
import { Badge, ModelChip, ProviderChip, StatusChip } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CompareIcon, PlayIcon, TraceIcon } from "@/components/ui/icons";

type Result = {
  id: string;
  trace_id: string;
  provider: string;
  model: string;
  status: string;
  latency_ms?: number | null;
  time_to_first_token_ms?: number | null;
  total_tokens: number;
  estimated_total_cost: number;
  output_preview: string;
  error_type?: string | null;
  error_category?: string | null;
  retry_count?: number;
  fallback_provider?: string | null;
};

type Run = {
  id: string;
  prompt: string;
  status: string;
  results: Result[];
};

type TargetSelection = {
  provider: string;
  model: string;
  selected: boolean;
};

export function ComparisonView() {
  const [prompt, setPrompt] = useState("Summarize why LLM observability matters.");
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [targets, setTargets] = useState<TargetSelection[]>([]);
  const [mockMode, setMockMode] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<ProviderCatalog>("/api/providers")
      .then((data) => {
        setModels(data.models);
        setMockMode(data.mock_mode);
        setTargets(
          data.providers.map((provider) => {
            const providerRows = getModelsForProvider(data.models, provider);
            const firstModel = getDefaultModelForProvider(data.models, provider);
            const available = providerRows.some((row) => row.available);
            return {
              provider,
              model: firstModel,
              selected: provider === "mock" || available,
            };
          })
        );
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load providers"));
  }, []);

  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    const timer = window.setInterval(() => {
      api<Run>(`/api/comparisons/${run.id}`).then(setRun).catch(() => undefined);
    }, 700);
    return () => window.clearInterval(timer);
  }, [run?.id, run?.status]);

  const selectedTargets = useMemo(
    () => targets.filter((target) => target.selected && target.model),
    [targets]
  );

  async function start() {
    if (!selectedTargets.length) {
      setError("Select at least one valid provider/model target.");
      return;
    }
    setRunning(true);
    setError("");
    try {
      const result = await api<Run>("/api/comparisons", {
        method: "POST",
        body: JSON.stringify({
          prompt,
          context_mode: "none",
          temperature: 0.7,
          max_tokens: 800,
          targets: selectedTargets.map((target) => ({
            provider: target.provider,
            model: target.model,
          }))
        })
      });
      setRun(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run comparison");
    } finally {
      setRunning(false);
    }
  }

  async function retryFailed() {
    if (!run) return;
    setRun(await api<Run>(`/api/comparisons/${run.id}/retry-failed`, { method: "POST" }));
  }

  const completed = [...(run?.results.filter((r) => r.status === "completed") || [])];
  const canRank = completed.length >= 2;
  const fastest = canRank ? [...completed].sort((a, b) => (a.latency_ms || 0) - (b.latency_ms || 0))[0] : undefined;
  const cheapest = canRank ? [...completed].sort((a, b) => a.estimated_total_cost - b.estimated_total_cost)[0] : undefined;
  const failedCount = run?.results.filter((item) => item.status !== "completed").length || 0;

  return (
    <main className="page-enter mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5">
        <p className="text-sm font-medium uppercase tracking-wide text-signal">Provider comparison</p>
        <h1 className="mt-1 text-2xl font-semibold">Compare provider behavior</h1>
        <p className="mt-1 max-w-2xl text-sm text-ink/55">
          Run the same prompt across providers/models and compare latency, tokens, cost, and failures.
        </p>
      </div>

      <section className="surface-card p-5">
        <label className="grid gap-2 text-sm font-medium text-ink/70">
          Prompt
          <textarea
            className="min-h-36 w-full resize-none rounded-xl border border-black/15 px-4 py-3 text-sm shadow-sm transition focus:border-signal focus:outline-none focus:ring-4 focus:ring-signal/10"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
        </label>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="grid flex-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {targets.map((target) => {
              const providerRows = getModelsForProvider(models, target.provider);
              const providerMeta = providerRows[0];
              return (
                <label
                  key={target.provider}
                  className="flex items-center gap-3 rounded-xl border border-black/10 bg-paper/70 px-3 py-2 text-sm"
                >
                  <input
                    checked={target.selected}
                    className="h-4 w-4 accent-[rgb(var(--color-signal))]"
                    onChange={(event) =>
                      setTargets((current) =>
                        current.map((item) =>
                          item.provider === target.provider
                            ? { ...item, selected: event.target.checked }
                            : item
                        )
                      )
                    }
                    type="checkbox"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <ProviderChip provider={target.provider} />
                      <Badge tone={providerMeta?.key_configured ? "success" : "warning"}>
                        {providerMeta?.status_label || "configured"}
                      </Badge>
                      {mockMode && target.provider === "mock" && <Badge>simulated response</Badge>}
                    </div>
                    <select
                      className="mt-2 w-full rounded-md border border-black/15 bg-white px-3 py-2 text-sm shadow-sm transition focus:border-signal focus:outline-none"
                      value={target.model}
                      onChange={(event) =>
                        setTargets((current) =>
                          current.map((item) =>
                            item.provider === target.provider
                              ? { ...item, model: event.target.value }
                              : item
                          )
                        )
                      }
                    >
                      {providerRows.map((row) => (
                        <option key={row.model} value={row.model}>
                          {row.model}
                        </option>
                      ))}
                    </select>
                  </div>
                </label>
              );
            })}
          </div>
          <Button onClick={start} disabled={running || !prompt.trim() || !selectedTargets.length}>
            <PlayIcon className="h-4 w-4" />
            {running ? "Running comparison" : "Run Comparison"}
          </Button>
        </div>
      </section>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {!run && (
        <div className="mt-5 grid min-h-64 place-items-center rounded-xl border border-dashed border-black/15 bg-white/70 p-8 text-center">
          <div>
            <div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-signal/10 text-signal">
              <CompareIcon className="h-6 w-6" />
            </div>
            <h2 className="mt-3 font-semibold">Run a comparison</h2>
            <p className="mt-1 text-sm text-ink/55">Run a comparison to see provider performance side by side.</p>
          </div>
        </div>
      )}

      {run && (
        <>
        <div className="mt-5 flex items-center justify-between rounded-xl border border-signal/20 bg-signal/5 p-3 text-sm">
          <span>Run status: <strong>{run.status}</strong> · {run.results.length} target result(s) persisted</span>
          {failedCount > 0 && <Button variant="secondary" onClick={retryFailed}>Retry {failedCount} failed target{failedCount === 1 ? "" : "s"}</Button>}
        </div>
        <section className="mt-5 grid gap-4 lg:grid-cols-3">
          {run.results.map((result) => (
            <article
              key={result.id || result.trace_id}
              className={`surface-card overflow-hidden p-4 ${result.status === "completed" ? "" : "border-red-500/20 bg-red-500/5"}`}
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <ProviderChip provider={result.provider} />
                    <ModelChip model={result.model} />
                  </div>
                </div>
                <StatusChip status={result.status === "completed" ? "completed" : "error"} />
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <Metric label="Latency" value={ms(result.latency_ms)} />
                <Metric label="TTFT" value={result.time_to_first_token_ms == null ? "Not measured" : ms(result.time_to_first_token_ms)} />
                <Metric label="Tokens" value={result.total_tokens} />
                <Metric label="Cost" value={money(result.estimated_total_cost)} />
                <Metric label="Error" value={result.error_category || result.error_type || "-"} />
                <div>
                  <div className="text-xs uppercase text-ink/45">Trace</div>
                  <Link className="mt-1 inline-flex items-center gap-1 font-medium text-signal underline" href={`/traces/${result.trace_id}`}>
                    <TraceIcon className="h-3.5 w-3.5" />
                    Open trace
                  </Link>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                {result.retry_count ? <Badge>{result.retry_count} retries</Badge> : null}
                {result.fallback_provider ? <Badge tone="warning">fallback: {result.fallback_provider}</Badge> : null}
                {result.status !== "completed" && <StatusChip status="error" />}
                {fastest?.trace_id === result.trace_id && <Badge tone="info">fastest successful result</Badge>}
                {cheapest?.trace_id === result.trace_id && <Badge tone="warning">cheapest successful result</Badge>}
                {completed.length === 1 && result.status === "completed" && <Badge tone="info">only successful target</Badge>}
              </div>
              <pre className="mt-4 max-h-52 overflow-auto whitespace-pre-wrap rounded-lg bg-paper p-3 text-xs leading-6">
                {result.output_preview || (result.status !== "completed" ? result.error_type || "Request failed before output." : "Output not retained because content capture is disabled.")}
              </pre>
            </article>
          ))}
        </section>
        </>
      )}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs uppercase text-ink/45">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
    </div>
  );
}
