export function formatDateTime(value?: string | null) {
  if (!value) {
    return "未提供";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDurationMs(value?: number | null) {
  if (typeof value !== "number") {
    return "未记录";
  }

  if (value < 1000) {
    return `${value} ms`;
  }

  return `${(value / 1000).toFixed(2)} s`;
}

export function formatPercent(value?: number | null) {
  if (typeof value !== "number") {
    return "未记录";
  }

  return `${value}%`;
}

export function formatNullableText(value?: string | null, fallback = "未提供") {
  return value && value.trim() ? value : fallback;
}
