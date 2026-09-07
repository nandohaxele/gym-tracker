import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle, RotateCw } from 'lucide-react';

import {
  addWorkoutExercise,
  completeWorkout,
  deleteWorkoutExercise,
  getWorkout,
  patchWorkout,
} from '@/api/workouts.js';
import { getLastWeights } from '@/api/exercises.js';
import { createSet, deleteSet, patchSet } from '@/api/sets.js';
import useAsync from '@/hooks/useAsync.js';
import { toDateInputValue } from '@/utils/format.js';
import {
  emptyDraftRow,
  hasPrimaryValue,
  lastWeightMap,
  shouldDeleteSetViaApi,
  shouldPersistSet,
  rowsForWorkoutExercise,
  setWritePayload,
  trackingOf,
} from '@/lib/tracking.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton from '@/components/ui/AppButton.jsx';
import WorkoutForm from '@/components/workouts/WorkoutForm.jsx';
import SaveAsTemplateDialog from '@/components/workouts/SaveAsTemplateDialog.jsx';

function sortExercises(exercises = []) {
  return [...exercises].sort((a, b) => a.order_index - b.order_index);
}

function buildBlocks(workout, weights) {
  return sortExercises(workout.exercises).map((we) => ({
    workout_exercise_id: we.id,
    exercise: we.exercise,
    planned_sets: we.planned_sets,
    planned_reps_min: we.planned_reps_min,
    planned_reps_max: we.planned_reps_max,
    planned_duration_seconds_min: we.planned_duration_seconds_min,
    planned_duration_seconds_max: we.planned_duration_seconds_max,
    planned_distance_meters_min: we.planned_distance_meters_min,
    planned_distance_meters_max: we.planned_distance_meters_max,
    rows: rowsForWorkoutExercise(we, weights[we.exercise.id]),
  }));
}

export default function WorkoutEditorPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const fetcher = useCallback(() => getWorkout(id), [id]);
  const { data: workout, error, loading, reload, setData } = useAsync(fetcher, [id]);

  const [name, setName] = useState('');
  const [date, setDate] = useState('');
  const [blocks, setBlocks] = useState([]);
  const [weights, setWeights] = useState({});
  const [serverError, setServerError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const blocksRef = useRef([]);

  useEffect(() => {
    if (!workout) return undefined;
    setName(workout.name);
    setDate(toDateInputValue(workout.date));
    let cancelled = false;
    const ids = (workout.exercises || []).map((we) => we.exercise.id);
    getLastWeights(ids, workout.id)
      .then((rows) => {
        if (cancelled) return;
        const map = lastWeightMap(rows);
        setWeights(map);
        const next = buildBlocks(workout, map);
        blocksRef.current = next;
        setBlocks(next);
      })
      .catch(() => {
        if (cancelled) return;
        setWeights({});
        const next = buildBlocks(workout, {});
        blocksRef.current = next;
        setBlocks(next);
      });
    return () => {
      cancelled = true;
    };
  }, [workout?.id]);

  const isActive = workout?.ended_at == null;

  const replaceBlock = (workoutExerciseId, updater) => {
    setBlocks((current) => {
      const next = current.map((block) =>
        block.workout_exercise_id === workoutExerciseId ? updater(block) : block
      );
      blocksRef.current = next;
      return next;
    });
  };

  const handleMetaBlur = async () => {
    if (!workout) return false;
    const trimmed = name.trim();
    if (!trimmed) {
      setServerError('Workout name is required');
      return false;
    }
    if (trimmed === workout.name && date === toDateInputValue(workout.date)) return true;
    try {
      setServerError(null);
      await patchWorkout(id, { name: trimmed, date });
      return true;
    } catch (err) {
      setServerError(err?.message || 'Could not save name or date.');
      return false;
    }
  };

  const handleAddExercise = async (exercise) => {
    setBusy(true);
    setServerError(null);
    try {
      const extra = await getLastWeights([exercise.id], id).catch(() => []);
      const nextWeights = { ...weights, ...lastWeightMap(extra) };
      setWeights(nextWeights);
      const created = await addWorkoutExercise(id, { exercise_id: exercise.id });
      setBlocks((current) => {
        const next = [
        ...current,
        {
          workout_exercise_id: created.id,
          exercise: created.exercise,
          planned_sets: created.planned_sets,
          planned_reps_min: created.planned_reps_min,
          planned_reps_max: created.planned_reps_max,
          planned_duration_seconds_min: created.planned_duration_seconds_min,
          planned_duration_seconds_max: created.planned_duration_seconds_max,
          planned_distance_meters_min: created.planned_distance_meters_min,
          planned_distance_meters_max: created.planned_distance_meters_max,
          rows: rowsForWorkoutExercise(created, nextWeights[exercise.id]),
        },
      ];
        blocksRef.current = next;
        return next;
      });
    } catch (err) {
      setServerError(err?.message || 'Could not add the exercise.');
    } finally {
      setBusy(false);
    }
  };

  const handleRemoveExercise = async (workoutExerciseId) => {
    setBusy(true);
    setServerError(null);
    try {
      await deleteWorkoutExercise(workoutExerciseId);
      setBlocks((current) => {
        const next = current.filter(
          (block) => block.workout_exercise_id !== workoutExerciseId
        );
        blocksRef.current = next;
        return next;
      });
    } catch (err) {
      setServerError(err?.message || 'Could not remove the exercise.');
    } finally {
      setBusy(false);
    }
  };

  const handleRowChange = (workoutExerciseId, setIndex, patch) => {
    replaceBlock(workoutExerciseId, (block) => ({
      ...block,
      rows: block.rows.map((row, index) =>
        index === setIndex ? { ...row, ...patch } : row
      ),
    }));
  };
  // replaceBlock already writes blocksRef before persist/commit reads it.

  const handleRowCommit = async (workoutExerciseId, setIndex) => {
    const block = blocksRef.current.find(
      (item) => item.workout_exercise_id === workoutExerciseId
    );
    if (!block) return;
    const row = block.rows[setIndex];
    if (!row) return;
    const tracking = trackingOf(block.exercise);
    if (!shouldPersistSet(row, tracking)) return;
    const primaryOk = hasPrimaryValue(row, tracking.primary);

    const payload = primaryOk
      ? setWritePayload(row, tracking)
      : row.weight_kg !== '' && row.weight_kg != null
        ? { weight_kg: Number(row.weight_kg) }
        : null;
    if (!payload) return;
    setBusy(true);
    setServerError(null);
    try {
      if (row.set_id) {
        const updated = await patchSet(row.set_id, payload);
        replaceBlock(workoutExerciseId, (current) => ({
          ...current,
          rows: current.rows.map((item, index) =>
            index === setIndex
              ? { ...item, set_id: updated.id, ...recordedPatch(updated) }
              : item
          ),
        }));
      } else {
        const created = await createSet(workoutExerciseId, payload);
        replaceBlock(workoutExerciseId, (current) => ({
          ...current,
          rows: current.rows.map((item, index) =>
            index === setIndex
              ? {
                  ...item,
                  clientKey: `set-${created.id}`,
                  set_id: created.id,
                  ...recordedPatch(created),
                }
              : item
          ),
        }));
      }
    } catch (err) {
      setServerError(err?.message || 'Could not save the set.');
    } finally {
      setBusy(false);
    }
  };

  const handleRowRemove = async (workoutExerciseId, setIndex) => {
    const block = blocksRef.current.find(
      (item) => item.workout_exercise_id === workoutExerciseId
    );
    if (!block) return;
    const row = block.rows[setIndex];
    if (!row) return;

    if (!shouldDeleteSetViaApi(row)) {
      replaceBlock(workoutExerciseId, (current) => ({
        ...current,
        rows:
          current.rows.length === 1
            ? [emptyDraftRow(current.exercise, current, weights[current.exercise.id])]
            : current.rows.filter((_, index) => index !== setIndex),
      }));
      return;
    }

    setBusy(true);
    setServerError(null);
    try {
      await deleteSet(row.set_id);
      replaceBlock(workoutExerciseId, (current) => {
        const next = current.rows.filter((_, index) => index !== setIndex);
        return {
          ...current,
          rows:
            next.length === 0
              ? [emptyDraftRow(current.exercise, current, weights[current.exercise.id])]
              : next,
        };
      });
    } catch (err) {
      setServerError(err?.message || 'Could not delete the set.');
    } finally {
      setBusy(false);
    }
  };

  const handleAddRow = (workoutExerciseId) => {
    replaceBlock(workoutExerciseId, (block) => ({
      ...block,
      rows: [
        ...block.rows,
        emptyDraftRow(block.exercise, {}, weights[block.exercise.id]),
      ],
    }));
  };

  const handleFinish = async () => {
    const metaOk = await handleMetaBlur();
    if (!metaOk) return;
    setBusy(true);
    setServerError(null);
    try {
      const updated = await completeWorkout(id);
      setData(updated);
      navigate(`/workouts/${id}`, { replace: true });
    } catch (err) {
      setServerError(err?.message || 'Could not finish the workout.');
      setBusy(false);
    }
  };

  const selectedLabel = useMemo(
    () => (isActive ? 'Active session' : 'Completed session'),
    [isActive]
  );

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate(`/workouts/${id}`)}
          aria-label="Back"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight">Edit workout</h1>
          <p className="text-xs text-muted-foreground">{selectedLabel}</p>
        </div>
      </header>

      {loading ? (
        <StatusView
          icon={Loader2}
          spinIcon
          title="Loading workout…"
          description="Fetching the session details."
        />
      ) : error ? (
        <StatusView
          icon={AlertCircle}
          tone="destructive"
          title="Couldn't load workout"
          description={error}
        >
          <AppButton variant="outline" onClick={reload}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </AppButton>
        </StatusView>
      ) : (
        <>
          <WorkoutForm
            name={name}
            date={date}
            onNameChange={setName}
            onDateChange={setDate}
            onMetaBlur={handleMetaBlur}
            exercises={blocks}
            onAddExercise={handleAddExercise}
            onRemoveExercise={handleRemoveExercise}
            onRowChange={handleRowChange}
            onRowCommit={handleRowCommit}
            onRowRemove={handleRowRemove}
            onAddRow={handleAddRow}
            onFinish={handleFinish}
            onSaveAsTemplate={() => setSaveOpen(true)}
            isActive={isActive}
            busy={busy}
            serverError={serverError}
          />
          <SaveAsTemplateDialog
            open={saveOpen}
            workoutId={id}
            workoutName={name}
            onClose={() => setSaveOpen(false)}
            onSaved={(template) => navigate(`/templates/${template.id}`)}
          />
        </>
      )}
    </PageContainer>
  );
}

function recordedPatch(set) {
  return {
    reps: set.reps ?? '',
    weight_kg: set.weight_kg ?? '',
    duration_seconds: set.duration_seconds ?? '',
    distance_meters: set.distance_meters ?? '',
  };
}
