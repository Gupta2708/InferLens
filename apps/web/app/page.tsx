import Image from "next/image";
import Link from "next/link";
import { ActivityIcon, CompareIcon, DatabaseIcon, PlugIcon, TraceIcon } from "@/components/ui/icons";
import { AnimatedBackground } from "@/components/landing/animated-background";
import { SignalFlowVisual } from "@/components/landing/signal-flow-visual";

const capabilities = [
  [TraceIcon, "Trace every request", "Inspect provider, model, latency, time to first token, tokens, estimated cost, errors, and request lifecycle.", "Latency · TTFT · Tokens · Cost"],
  [ActivityIcon, "Recover from failures", "See retries, fallback routing, circuit-breaker events, cancellations, and normalized provider errors.", "Retry · Fallback · Circuit breaker"],
  [PlugIcon, "Replay safely", "Re-run a request with another provider or model while preserving the original trace.", "Original trace · New execution"],
  [CompareIcon, "Compare providers", "Run the same prompt across multiple models and compare latency, tokens, cost, status, and output.", "Latency · Cost · Output · Status"],
] as const;

const technologies = ["Next.js", "TypeScript", "FastAPI", "PostgreSQL", "Redis Streams", "OpenTelemetry", "Prometheus", "Docker", "OpenAI", "Gemini"];
const features = ["Real SSE streaming", "Retry and fallback routing", "Circuit breaker", "W3C Trace Context", "PII redaction", "Dead-letter recovery", "Concurrent comparisons"];

export default function Home() {
  return <main className="landing-shell">
    <header className="landing-header">
      <div className="landing-container flex items-center justify-between gap-4 py-4">
        <Link href="/" className="brand-link" aria-label="InferLens home"><span className="logo-mark-shell"><Image src="/inferlens-mark.svg" alt="" width={42} height={42} className="logo-mark-image" priority /></span><span className="brand-title">Infer<span>Lens</span></span></Link>
        <nav className="hidden items-center gap-6 text-sm text-ink/65 sm:flex" aria-label="Landing navigation"><a className="landing-nav-link" href="#capabilities">Capabilities</a><a className="landing-nav-link" href="#stack">Stack</a><Link className="landing-console-link" href="/chat">Open console</Link></nav>
        <Link className="landing-console-link sm:hidden" href="/chat">Console</Link>
      </div>
    </header>
    <section className="landing-hero" aria-labelledby="hero-title">
      <AnimatedBackground />
      <div className="landing-container landing-hero-layout relative py-20 sm:py-24">
        <div>
        <p className="landing-eyebrow">LLM Gateway &amp; Observability</p>
        <h1 id="hero-title" className="landing-title">See what happens<br />behind every LLM<br /><span>response</span></h1>
        <p className="landing-lede">Route requests across providers, inspect latency and cost, trace failures, replay prompts, and compare models from one operational console.</p>
        <div className="mt-8 flex flex-wrap gap-3"><Link href="/chat" className="landing-primary">Explore InferLens <span aria-hidden="true">→</span></Link><a href="#capabilities" className="landing-secondary">View capabilities</a></div>
        <p className="mt-7 text-sm text-ink/50">Built with FastAPI, Next.js, Redis Streams, PostgreSQL, OpenTelemetry, and Prometheus.</p>
        </div><SignalFlowVisual />
      </div>
    </section>
    <section id="capabilities" className="landing-container landing-reveal scroll-mt-24 py-16 sm:py-20"><p className="landing-eyebrow">Operational clarity</p><h2 className="landing-section-title">One console for the full request lifecycle</h2><div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{capabilities.map(([Icon, title, copy, detail]) => <article className="landing-card" key={title}><div className="landing-icon"><Icon className="h-5 w-5" /></div><h3>{title}</h3><p>{copy}</p><small>{detail}</small></article>)}</div></section>
    <section id="stack" className="landing-stack scroll-mt-24"><div className="landing-container landing-reveal py-16 sm:py-20"><p className="landing-eyebrow">Technical stack</p><h2 className="landing-section-title">Built as real LLM infrastructure</h2><p className="landing-copy">InferLens combines a provider-agnostic gateway, asynchronous ingestion, privacy-safe observability, and resilient worker processing.</p><p className="landing-row-label">Core stack</p><div className="landing-chip-row">{technologies.slice(0, 6).map((item) => <span key={item}>{item}</span>)}</div><p className="landing-row-label">Observability &amp; providers</p><div className="landing-chip-row">{technologies.slice(6).map((item) => <span key={item}>{item}</span>)}</div><div className="landing-feature-row mt-6">{features.map((item) => <span key={item}>✓ {item}</span>)}</div></div></section>
    <section className="landing-container py-16 sm:py-20"><div className="landing-cta"><p className="landing-eyebrow">Start exploring</p><h2 className="landing-section-title">Observe your first LLM request</h2><p className="landing-copy">Open the InferLens console to explore streaming, traces, replay, comparisons, latency, tokens, cost, and provider behavior.</p><Link href="/chat" className="landing-primary mt-7">Open the console <span aria-hidden="true">→</span></Link></div></section>
    <footer className="border-t border-black/10"><div className="landing-container flex flex-col gap-2 py-7 text-sm text-ink/50 sm:flex-row sm:items-center sm:justify-between"><span><strong className="text-ink/80">InferLens</strong> · Provider-agnostic LLM gateway and observability platform</span><span>Built by the project author · {new Date().getFullYear()}</span></div></footer>
  </main>;
}
