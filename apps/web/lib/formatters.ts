export function money(value: number) {
  if (!value) return "$0";
  if (value < 0.000001) return "< $0.000001";
  if (value < 0.01) return `$${value.toFixed(6).replace(/0+$/, "").replace(/\.$/, "")}`;
  return `$${value.toFixed(4)}`;
}

export function ms(value?: number | null) {
  return value == null ? "-" : `${value} ms`;
}

export function compactDate(value?: string | null) {
  if (!value) return "-";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function percent(value?: number | null) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function shortTraceId(traceId: string) {
  return traceId.length <= 18 ? traceId : `${traceId.slice(0, 10)}...${traceId.slice(-6)}`;
}
