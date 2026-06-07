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

/**
 * toDateInputValue - normalize a Date | ISO string | timestamp into the
 * `YYYY-MM-DD` string expected by <input type="date"> and the backend.
 * Falls back to today's local date when the value is missing/invalid.
 */
export function toDateInputValue(value) {
  const d = value ? new Date(value) : new Date();
  const safe = Number.isNaN(d.getTime()) ? new Date() : d;
  const year = safe.getFullYear();
  const month = String(safe.getMonth() + 1).padStart(2, '0');
  const day = String(safe.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}
