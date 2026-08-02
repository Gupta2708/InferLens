export function AnimatedBackground() {
  return <div className="landing-motion" aria-hidden="true">
    <div className="landing-grid" /><div className="landing-noise" />
    <div className="landing-wave landing-wave-a" /><div className="landing-wave landing-wave-b" />
    <svg className="landing-routes" viewBox="0 0 1200 620" preserveAspectRatio="none"><path d="M-40 420C180 230 320 530 520 300S850 140 1240 310" /><path d="M-30 175C230 310 360 90 620 250S930 450 1230 115" /><circle className="signal-node node-a" r="5"><animateMotion dur="13s" repeatCount="indefinite" path="M-40 420C180 230 320 530 520 300S850 140 1240 310" /></circle><circle className="signal-node node-b" r="4"><animateMotion dur="17s" repeatCount="indefinite" path="M-30 175C230 310 360 90 620 250S930 450 1230 115" /></circle></svg>
  </div>;
}
