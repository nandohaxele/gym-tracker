// Live Session editor. Draft set rows stay client-side until the primary
// metric is recorded via granular Set APIs.

import { useState } from 'react';
import { AlertCircle, Check, Dumbbell, Plus } from 'lucide-react';

import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';
import ExerciseFieldCard from './ExerciseFieldCard.jsx';
import ExercisePicker from './ExercisePicker.jsx';
import { formatPlannedHint } from '@/lib/tracking.js';

const NAME_SUGGESTIONS = [
  'Chest Day',
  'Leg Day',
  'Back Day',
  'Arms Day',
  'Shoulders Day',
  'Biceps and Triceps Day',
  'Calf Day',
  'Powerlifting Day',
  'Abs',
  'Stretching',
];

export default function WorkoutForm({
  name,
  date,
  onNameChange,
  onDateChange,
  onMetaBlur,
  exercises = [],
  onAddExercise,
  onRemoveExercise,
  onRowChange,
  onRowCommit,
  onRowRemove,
  onAddRow,
  onAskAssistant,
  onFinish,
  onSaveAsTemplate,
  isActive,
  busy = false,
  serverError,
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [showNameSuggestions, setShowNameSuggestions] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      {serverError && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{serverError}</span>
        </div>
      )}

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2">
          <AppInput
            label="Workout name"
            placeholder="e.g. Push Day"
            autoComplete="off"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            onFocus={() => setShowNameSuggestions(true)}
            onBlur={(e) => {
              setShowNameSuggestions(false);
              onMetaBlur?.(e);
            }}
          />

          {showNameSuggestions && (
            <div
              role="listbox"
              aria-label="Workout name suggestions"
              className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
            >
              {NAME_SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => onNameChange(suggestion)}
                  className="shrink-0 whitespace-nowrap rounded-full border border-input bg-secondary px-3.5 py-2 text-sm font-medium text-secondary-foreground transition-colors hover:bg-accent active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>

        <AppInput
          label="Date"
          type="date"
          value={date}
          onChange={(e) => onDateChange(e.target.value)}
          onBlur={onMetaBlur}
        />
      </div>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Exercises
          </h2>
          <span className="text-xs text-muted-foreground">{exercises.length}</span>
        </div>

        {exercises.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Dumbbell className="h-6 w-6" aria-hidden="true" />
            </div>
            <p className="text-sm text-muted-foreground">
              Add exercises. Planned rows stay local until you record a set.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {exercises.map((block) => (
              <ExerciseFieldCard
                key={block.workout_exercise_id}
                exercise={block.exercise}
                rows={block.rows}
                plannedHint={formatPlannedHint(block)}
                busy={busy}
                onAskAssistant={
                  onAskAssistant
                    ? () => onAskAssistant(block.workout_exercise_id)
                    : undefined
                }
                onRowChange={(setIndex, patch) =>
                  onRowChange(block.workout_exercise_id, setIndex, patch)
                }
                onRowCommit={(setIndex) =>
                  onRowCommit(block.workout_exercise_id, setIndex)
                }
                onRowRemove={(setIndex) =>
                  onRowRemove(block.workout_exercise_id, setIndex)
                }
                onAddRow={() => onAddRow(block.workout_exercise_id)}
                onRemoveExercise={() => onRemoveExercise(block.workout_exercise_id)}
              />
            ))}
          </div>
        )}

        <AppButton
          type="button"
          variant="outline"
          block
          disabled={busy}
          onClick={() => setPickerOpen(true)}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add exercise
        </AppButton>
      </section>

      <div className="flex flex-col gap-3 pt-2">
        {isActive && (
          <AppButton type="button" block size="lg" disabled={busy} onClick={onFinish}>
            <Check className="h-4 w-4" aria-hidden="true" />
            Finish Workout
          </AppButton>
        )}
        <AppButton
          type="button"
          variant="outline"
          block
          disabled={busy}
          onClick={onSaveAsTemplate}
        >
          Save as My Template
        </AppButton>
      </div>

      {pickerOpen && (
        <ExercisePicker
          onPick={onAddExercise}
          onClose={() => setPickerOpen(false)}
          selectedIds={exercises.map((block) => Number(block.exercise.id))}
        />
      )}
    </div>
  );
}
