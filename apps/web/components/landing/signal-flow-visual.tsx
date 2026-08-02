export function SignalFlowVisual() {
  return <aside className="signal-flow" aria-label="Example request lifecycle">
    <div className="signal-flow-head"><span className="signal-pulse" /> Live request signal</div>
    {["Request received", "Gemini selected", "First token · 421 ms", "Trace persisted"].map((step, index) => <div className="signal-step" key={step}><span>{index + 1}</span><p>{step}</p><i /></div>)}
    <div className="signal-flow-foot"><span>trace_7f2a…91c</span><span>streaming</span></div>
  </aside>;
}
