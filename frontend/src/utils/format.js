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
  if (kg == null || kg === '') return '';
  return `${kg} ${unit}`;
}

export function formatDuration(totalSeconds) {
  if (totalSeconds == null || totalSeconds === '') return '';
  const n = Number(totalSeconds);
  if (!Number.isFinite(n) || n <= 0) return '';
  const minutes = Math.floor(n / 60);
  const seconds = n % 60;
  if (minutes === 0) return `${seconds}s`;
  if (seconds === 0) return `${minutes}m`;
  return `${minutes}m ${seconds}s`;
}

export function formatDistance(meters) {
  if (meters == null || meters === '') return '';
  const n = Number(meters);
  if (!Number.isFinite(n) || n <= 0) return '';
  if (n >= 1000 && n % 1000 === 0) return `${n / 1000} km`;
  if (n >= 1000) return `${(n / 1000).toFixed(2).replace(/\.?0+$/, '')} km`;
  return `${n} m`;
}

export function secondsToParts(totalSeconds) {
  if (totalSeconds == null || totalSeconds === '') {
    return { minutes: '', seconds: '' };
  }
  const n = Number(totalSeconds);
  if (!Number.isFinite(n) || n < 0) return { minutes: '', seconds: '' };
  return {
    minutes: String(Math.floor(n / 60)),
    seconds: String(n % 60),
  };
}

export function partsToSeconds(minutes, seconds) {
  const emptyMin = minutes === '' || minutes == null;
  const emptySec = seconds === '' || seconds == null;
  if (emptyMin && emptySec) return null;
  const m = emptyMin ? 0 : Number(minutes);
  const s = emptySec ? 0 : Number(seconds);
  if (!Number.isFinite(m) || !Number.isFinite(s)) return null;
  const total = m * 60 + s;
  return total > 0 ? total : null;
}

export function metersToKmInput(meters) {
  if (meters == null || meters === '') return '';
  const n = Number(meters);
  if (!Number.isFinite(n) || n <= 0) return '';
  const km = n / 1000;
  return String(Number(km.toFixed(3)));
}

export function kmInputToMeters(km) {
  if (km === '' || km == null) return null;
  const n = Number(km);
  if (!Number.isFinite(n) || n <= 0) return null;
  return Math.round(n * 1000);
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
