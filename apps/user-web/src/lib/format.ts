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

export function formatNullableText(value?: string | null, fallback = "未设置") {
  return value && value.trim() ? value : fallback;
}
