// Display formatters. Keep i18n-ready (use Intl APIs).

export function formatDate(value) {
  // Italian-friendly numeric format (dd/MM/yyyy), e.g. 19/06/2026.
  // Note: native <input type="date"> stays browser-locale driven on purpose.
  if (!value) return '';
  const d = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  return new Intl.DateTimeFormat('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
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
