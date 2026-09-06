// ExerciseFieldCard - one Session exercise with recorded Sets + client drafts.

import { Plus, X } from 'lucide-react';
import AppButton from '@/components/ui/AppButton.jsx';
import SetRow from './SetRow.jsx';
import { formatPlannedHint, trackingOf } from '@/lib/tracking.js';

export default function ExerciseFieldCard({
  exercise,
  rows,
  plannedHint,
  onRowChange,
  onRowCommit,
  onRowRemove,
  onAddRow,
  onRemoveExercise,
  busy = false,
}) {
  const tracking = trackingOf(exercise);
  const hint = plannedHint || formatPlannedHint({ ...exercise });

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-semibold leading-tight">{exercise.name}</p>
          {exercise.muscle_group && (
            <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
              {exercise.muscle_group}
            </p>
          )}
          {hint && (
            <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
          )}
        </div>
        <button
          type="button"
          onClick={onRemoveExercise}
          disabled={busy}
          aria-label={`Remove ${exercise.name || 'exercise'}`}
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div className="flex flex-col gap-2">
        {rows.map((row, setIndex) => (
          <SetRow
            key={row.clientKey}
            index={setIndex}
            row={row}
            tracking={tracking}
            busy={busy}
            onChange={(patch) => onRowChange(setIndex, patch)}
            onCommit={() => onRowCommit(setIndex)}
            onRemove={() => onRowRemove(setIndex)}
            canRemove={rows.length > 1 || Boolean(row.set_id)}
          />
        ))}
      </div>

      <AppButton
        type="button"
        variant="ghost"
        size="sm"
        disabled={busy}
        onClick={onAddRow}
        className="self-start"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        Add set
      </AppButton>
    </div>
  );
}
