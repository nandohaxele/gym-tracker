// WorkoutForm - create/edit form shared by /workouts/new and /workouts/:id/edit.
// Handles workout name + date, a field array of exercises (each with its own
// nested field array of sets), validation via the shared zod workoutSchema, and
// transforms form values into the backend payload before delegating to onSubmit.

import { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Dumbbell, Plus } from 'lucide-react';

import { workoutSchema } from '@/lib/validators.js';
import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';
import ExerciseFieldCard from './ExerciseFieldCard.jsx';
import ExercisePicker from './ExercisePicker.jsx';

// Map validated form values -> backend WorkoutCreate/WorkoutUpdate payload.
// order_index is derived from array position; UI-only fields are dropped.
function toPayload(values) {
  return {
    name: values.name.trim(),
    date: values.date,
    exercises: values.exercises.map((ex, exIndex) => ({
      exercise_id: Number(ex.exercise_id),
      order_index: exIndex,
      sets: ex.sets.map((set, setIndex) => ({
        reps: Number(set.reps),
        weight: Number(set.weight),
        order_index: setIndex,
      })),
    })),
  };
}

export default function WorkoutForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = 'Save workout',
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [serverError, setServerError] = useState(null);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(workoutSchema),
    defaultValues,
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'exercises',
  });

  const selectedIds = fields.map((f) => Number(f.exercise_id));

  const handlePick = (exercise) => {
    append({
      exercise_id: exercise.id,
      name: exercise.name,
      muscle_group: exercise.muscle_group,
      sets: [{ reps: '', weight: '' }],
    });
  };

  const submit = async (values) => {
    setServerError(null);
    try {
      await onSubmit(toPayload(values));
    } catch (err) {
      setServerError(err?.message || 'Could not save the workout. Please try again.');
    }
  };

  const exercisesError =
    errors.exercises?.root?.message || errors.exercises?.message;

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-6">
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
        <AppInput
          label="Workout name"
          placeholder="e.g. Push day"
          autoComplete="off"
          error={errors.name?.message}
          {...register('name')}
        />
        <AppInput
          label="Date"
          type="date"
          error={errors.date?.message}
          {...register('date')}
        />
      </div>

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Exercises
          </h2>
          <span className="text-xs text-muted-foreground">{fields.length}</span>
        </div>

        {fields.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Dumbbell className="h-6 w-6" aria-hidden="true" />
            </div>
            <p className="text-sm text-muted-foreground">
              Add exercises and log your sets.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {fields.map((field, index) => (
              <ExerciseFieldCard
                key={field.id}
                control={control}
                register={register}
                exerciseIndex={index}
                field={field}
                errors={errors.exercises?.[index]}
                onRemove={() => remove(index)}
              />
            ))}
          </div>
        )}

        {exercisesError && (
          <p className="text-sm font-medium text-destructive">{exercisesError}</p>
        )}

        <AppButton
          type="button"
          variant="outline"
          block
          onClick={() => setPickerOpen(true)}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add exercise
        </AppButton>
      </section>

      <div className="flex flex-col gap-3 pt-2 sm:flex-row-reverse">
        <AppButton type="submit" block size="lg" loading={isSubmitting}>
          {isSubmitting ? 'Saving…' : submitLabel}
        </AppButton>
        <AppButton type="button" variant="ghost" block onClick={onCancel}>
          Cancel
        </AppButton>
      </div>

      {pickerOpen && (
        <ExercisePicker
          onPick={handlePick}
          onClose={() => setPickerOpen(false)}
          selectedIds={selectedIds}
        />
      )}
    </form>
  );
}
