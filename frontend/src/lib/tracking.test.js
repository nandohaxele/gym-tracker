import { describe, expect, it } from 'vitest';

import { kmInputToMeters, partsToSeconds } from '@/utils/format.js';
import {
  emptyDraftRow,
  exerciseDisplayName,
  formatPlannedHint,
  formatSetLine,
  hasPrimaryValue,
  isArchivedExercise,
  lastWeightMap,
  recordedRowFromSet,
  rowsForWorkoutExercise,
  setWritePayload,
  shouldDeleteSetViaApi,
  shouldPersistSet,
  trackingOf,
} from './tracking.js';

const repsExercise = {
  id: 1,
  name: 'Bench Press',
  primary_tracking_type: 'reps',
  secondary_tracking_types: [],
  is_active: true,
};

const durationExercise = {
  id: 2,
  name: 'Plank',
  primary_tracking_type: 'duration',
  secondary_tracking_types: [],
  is_active: true,
};

describe('draft vs recorded rows', () => {
  it('turns planned_* into drafts without set_id', () => {
    const we = {
      exercise: repsExercise,
      planned_sets: 3,
      planned_reps_min: 8,
      sets: [],
    };
    const rows = rowsForWorkoutExercise(we, 40);
    expect(rows).toHaveLength(3);
    expect(rows.every((row) => row.set_id === undefined)).toBe(true);
    expect(rows[0].reps).toBe(8);
    expect(rows[0].weight_kg).toBe(40);
    expect(rows.every((row) => !hasPrimaryValue(row, 'reps') || row.reps === 8)).toBe(true);
    expect(rows.every((row) => !shouldDeleteSetViaApi(row))).toBe(true);
  });

  it('keeps persisted set_id and pads remaining planned drafts', () => {
    const we = {
      exercise: repsExercise,
      planned_sets: 3,
      sets: [{ id: 38, order_index: 0, reps: 8, weight_kg: 60 }],
    };
    const rows = rowsForWorkoutExercise(we);
    expect(rows[0].set_id).toBe(38);
    expect(rows[0].clientKey).toBe('set-38');
    expect(rows).toHaveLength(3);
    expect(rows[1].set_id).toBeUndefined();
  });

  it('does not treat an untouched draft as recorded', () => {
    const draft = emptyDraftRow(repsExercise, {}, '');
    expect(hasPrimaryValue(draft, 'reps')).toBe(false);
    expect(shouldPersistSet(draft, trackingOf(repsExercise))).toBe(false);
    expect(setWritePayload(draft, trackingOf(repsExercise))).toEqual({});
  });
});

describe('payloads and conversions', () => {
  it('writes reps and optional weight, and keeps 0 distinct from empty', () => {
    const tracking = trackingOf(repsExercise);
    expect(
      setWritePayload(
        { reps: 8, weight_kg: 0, duration_seconds: '', distance_meters: '' },
        tracking
      )
    ).toEqual({ reps: 8, weight_kg: 0 });
    expect(
      setWritePayload(
        { reps: 8, weight_kg: '', duration_seconds: '', distance_meters: '' },
        tracking
      )
    ).toEqual({ reps: 8 });
  });

  it('converts duration parts to seconds and distance km to meters', () => {
    expect(partsToSeconds(1, 30)).toBe(90);
    expect(kmInputToMeters('1.5')).toBe(1500);
    const tracking = trackingOf(durationExercise);
    expect(
      setWritePayload(
        {
          reps: '',
          weight_kg: '',
          duration_seconds: partsToSeconds(1, 15),
          distance_meters: '',
        },
        tracking
      )
    ).toEqual({ duration_seconds: 75 });
  });

  it('only includes configured tracking fields', () => {
    const payload = setWritePayload(
      {
        reps: 10,
        weight_kg: 20,
        duration_seconds: 30,
        distance_meters: 400,
      },
      trackingOf(repsExercise)
    );
    expect(payload).toEqual({ reps: 10, weight_kg: 20 });
    expect(payload).not.toHaveProperty('duration_seconds');
    expect(payload).not.toHaveProperty('distance_meters');
  });
});

describe('persist / delete guards', () => {
  const tracking = trackingOf(repsExercise);

  it('does not persist a draft without the primary metric', () => {
    expect(
      shouldPersistSet({ weight_kg: 40 }, tracking)
    ).toBe(false);
  });

  it('persists a draft once the primary metric is present', () => {
    expect(shouldPersistSet({ reps: 8, weight_kg: 40 }, tracking)).toBe(true);
  });

  it('deletes via API only when a set_id exists', () => {
    expect(shouldDeleteSetViaApi(emptyDraftRow(repsExercise))).toBe(false);
    expect(shouldDeleteSetViaApi({ set_id: 12 })).toBe(true);
  });
});

describe('formatting and last-weight', () => {
  it('formats planned ranges and last-weight map', () => {
    expect(
      formatPlannedHint({
        planned_sets: 3,
        planned_reps_min: 8,
        planned_reps_max: 10,
      })
    ).toBe('3 sets · 8 reps–10 reps');
    expect(lastWeightMap([{ exercise_id: 1, weight_kg: 0 }])).toEqual({ 1: 0 });
  });

  it('formats historical set 38 without inventing duration', () => {
    const set38 = {
      id: 38,
      reps: 200,
      weight_kg: 96,
      duration_seconds: null,
      distance_meters: null,
    };
    expect(formatSetLine(set38)).toBe('200 reps · 96 kg');
    const row = recordedRowFromSet(set38);
    expect(row.set_id).toBe(38);
    expect(row.duration_seconds).toBe('');
  });

  it('null-safes archived exercise labels', () => {
    expect(exerciseDisplayName(null)).toBe('Unknown exercise');
    expect(isArchivedExercise({ is_active: false })).toBe(true);
    expect(isArchivedExercise({ is_active: true })).toBe(false);
  });
});
