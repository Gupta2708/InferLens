"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money } from "@/lib/formatters";
import type { ProviderCatalog, ProviderModel } from "@/lib/types";
import { ModelChip, ProviderChip, StatusChip } from "@/components/ui/badge";
import { PlugIcon } from "@/components/ui/icons";

export default function ProvidersPage() {
  const [models, setModels] = useState<ProviderModel[]>([]);
  const [mockMode, setMockMode] = useState(false);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await api<ProviderCatalog>("/api/providers");
      setModels(data.models);
      setMockMode(data.mock_mode);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load providers");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <main className="page-enter mx-auto max-w-7xl px-4 py-6">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
        <p className="text-sm font-medium uppercase tracking-wide text-signal">Gateway configuration</p>
        <h1 className="mt-1 text-2xl font-semibold">Providers</h1>
        <p className="mt-1 text-sm text-ink/55">Configuration state is safe to refresh and does not make a billable live-provider request.</p>
        </div>
        <button onClick={() => void load()} disabled={refreshing} className="focus-ring rounded-md border border-signal/25 bg-signal/10 px-3 py-2 text-sm font-semibold text-signal disabled:opacity-50">
          {refreshing ? "Refreshing…" : "Refresh status"}
        </button>
      </div>

      {mockMode && <div className="mb-4 rounded-xl border border-signal/20 bg-signal/10 p-4 text-sm text-signal"><strong>Mock mode / simulated responses.</strong> No real provider key is active, or Mock mode was explicitly forced. Traces, logs, metrics, replays, and comparisons record provider <code>mock</code>.</div>}

      {error && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {models.map((item) => {
          return (
            <article key={`${item.provider}-${item.model}`} className="surface-card p-5 hover:-translate-y-0.5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="grid h-11 w-11 place-items-center rounded-xl bg-signal/10 text-signal">
                    <PlugIcon className="h-5 w-5" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <ProviderChip provider={item.provider} />
                      <ModelChip model={item.model} />
                    </div>
                  </div>
                </div>
                <StatusChip status={item.status_label} />
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
                <ProviderMetric label="Streaming" value={item.supports_streaming ? "supported" : "not supported"} />
                <ProviderMetric label="Configuration" value={item.provider === "mock" ? "Mock available" : item.key_configured ? "Configured" : "Not configured"} />
                <ProviderMetric label="Availability" value={item.status_label} />
                <ProviderMetric label="Model status" value="model configurable" />
                <ProviderMetric label="Input / 1k" value={formatRate(item.input_cost_per_1k_tokens)} />
                <ProviderMetric label="Output / 1k" value={formatRate(item.output_cost_per_1k_tokens)} />
              </div>
            </article>
          );
        })}
      </section>

      {!models.length && !error && (
        <div className="grid min-h-64 place-items-center rounded-xl border border-dashed border-black/15 bg-white/70 p-8 text-center text-sm text-ink/55">
          No provider configs returned by the API.
        </div>
      )}
    </main>
  );
}

function ProviderMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-paper/70 p-3">
      <div className="text-xs uppercase text-ink/45">{label}</div>
      <div className="mt-1 font-medium">{value}</div>
    </div>
  );
}

function formatRate(value?: number | null) {
  return value == null ? "not exposed" : money(value);
}
