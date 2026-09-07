import { formatDistance, formatDuration } from '@/utils/format.js';

export const TRACKING_TYPES = ['reps', 'duration', 'distance'];

export function trackingOf(exercise) {
  return {
    primary: exercise?.primary_tracking_type || 'reps',
    secondaries: exercise?.secondary_tracking_types || [],
  };
}

export function showsField(tracking, field) {
  if (field === 'weight_kg') return true;
  return (
    tracking.primary === field || tracking.secondaries.includes(field)
  );
}

export function hasPrimaryValue(row, primary) {
  if (primary === 'reps') return Number(row.reps) > 0;
  if (primary === 'duration') return Number(row.duration_seconds) > 0;
  if (primary === 'distance') return Number(row.distance_meters) > 0;
  return false;
}

export function shouldPersistSet(row, tracking) {
  const primaryOk = hasPrimaryValue(row, tracking.primary);
  if (!row.set_id && !primaryOk) return false;
  if (primaryOk) return true;
  return row.weight_kg !== '' && row.weight_kg != null;
}

export function shouldDeleteSetViaApi(row) {
  return Boolean(row.set_id);
}

export function exerciseDisplayName(exercise) {
  return exercise?.name || 'Unknown exercise';
}

export function isArchivedExercise(exercise) {
  return exercise?.is_active === false;
}

export function setWritePayload(row, tracking) {
  const payload = {};
  const applyMetric = (type) => {
    if (type === 'reps' && row.reps !== '' && row.reps != null) {
      payload.reps = Number(row.reps);
    }
    if (
      type === 'duration' &&
      row.duration_seconds !== '' &&
      row.duration_seconds != null
    ) {
      payload.duration_seconds = Number(row.duration_seconds);
    }
    if (
      type === 'distance' &&
      row.distance_meters !== '' &&
      row.distance_meters != null
    ) {
      payload.distance_meters = Number(row.distance_meters);
    }
  };

  applyMetric(tracking.primary);
  for (const secondary of tracking.secondaries) applyMetric(secondary);

  if (row.weight_kg !== '' && row.weight_kg != null) {
    payload.weight_kg = Number(row.weight_kg);
  }
  return payload;
}

function newClientKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `row-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function emptyDraftRow(exercise, planned = {}, lastWeightKg) {
  const primary = trackingOf(exercise).primary;
  return {
    clientKey: newClientKey(),
    set_id: undefined,
    reps: primary === 'reps' ? planned.planned_reps_min ?? '' : '',
    weight_kg: lastWeightKg ?? '',
    duration_seconds:
      primary === 'duration' ? planned.planned_duration_seconds_min ?? '' : '',
    distance_meters:
      primary === 'distance' ? planned.planned_distance_meters_min ?? '' : '',
  };
}

export function recordedRowFromSet(set) {
  return {
    clientKey: `set-${set.id}`,
    set_id: set.id,
    reps: set.reps ?? '',
    weight_kg: set.weight_kg ?? '',
    duration_seconds: set.duration_seconds ?? '',
    distance_meters: set.distance_meters ?? '',
  };
}

export function rowsForWorkoutExercise(we, lastWeightKg) {
  const recorded = [...(we.sets || [])]
    .sort((a, b) => a.order_index - b.order_index)
    .map(recordedRowFromSet);
  const plannedCount = we.planned_sets > 0 ? we.planned_sets : 0;
  const draftsNeeded =
    recorded.length === 0
      ? Math.max(plannedCount, 1)
      : Math.max(0, plannedCount - recorded.length);
  const drafts = Array.from({ length: draftsNeeded }, () =>
    emptyDraftRow(we.exercise, we, lastWeightKg)
  );
  return [...recorded, ...drafts];
}

function rangeText(min, max, format) {
  if (min == null && max == null) return '';
  if (min === max || max == null) return format(min);
  if (min == null) return format(max);
  return `${format(min)}–${format(max)}`;
}

export function formatPlannedHint(we) {
  if (!we) return '';
  const parts = [];
  if (we.planned_sets) parts.push(`${we.planned_sets} sets`);
  const reps = rangeText(
    we.planned_reps_min,
    we.planned_reps_max,
    (n) => `${n} reps`
  );
  const duration = rangeText(
    we.planned_duration_seconds_min,
    we.planned_duration_seconds_max,
    formatDuration
  );
  const distance = rangeText(
    we.planned_distance_meters_min,
    we.planned_distance_meters_max,
    formatDistance
  );
  if (reps) parts.push(reps);
  if (duration) parts.push(duration);
  if (distance) parts.push(distance);
  return parts.join(' · ');
}

export function formatSetLine(set) {
  const bits = [];
  if (set.reps != null) bits.push(`${set.reps} reps`);
  if (set.duration_seconds != null) bits.push(formatDuration(set.duration_seconds));
  if (set.distance_meters != null) bits.push(formatDistance(set.distance_meters));
  if (set.weight_kg != null) bits.push(`${set.weight_kg} kg`);
  return bits.filter(Boolean).join(' · ') || 'Logged';
}

export function lastWeightMap(rows = []) {
  const map = {};
  for (const row of rows) {
    map[row.exercise_id] = row.weight_kg;
  }
  return map;
}
