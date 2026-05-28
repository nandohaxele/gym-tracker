// Display formatters. Keep i18n-ready (use Intl APIs).

export function formatDate(value) {
  // TODO: accept Date | string | number; return locale-aware short date.
  if (!value) return '';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(d);
}

export function formatWeight(kg, unit = 'kg') {
  // TODO: support lb conversion if a user setting is added later.
  if (kg == null) return '';
  return `${kg} ${unit}`;
}
