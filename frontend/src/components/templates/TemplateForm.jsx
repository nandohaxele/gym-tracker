import { useState } from 'react';
import { useFieldArray, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Dumbbell, Plus } from 'lucide-react';

import { templateSchema } from '@/lib/validators.js';
import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';
import ExercisePicker from '@/components/workouts/ExercisePicker.jsx';
import TemplateExerciseCard from './TemplateExerciseCard.jsx';

function toPayload(values) {
  return {
    name: values.name.trim(),
    exercises: values.exercises.map((ex, index) => ({
      exercise_id: Number(ex.exercise_id),
      order_index: index,
      target_sets: Number(ex.target_sets),
      target_reps_min: emptyToNull(ex.target_reps_min),
      target_reps_max: emptyToNull(ex.target_reps_max),
      target_duration_seconds_min: emptyToNull(ex.target_duration_seconds_min),
      target_duration_seconds_max: emptyToNull(ex.target_duration_seconds_max),
      target_distance_meters_min: emptyToNull(ex.target_distance_meters_min),
      target_distance_meters_max: emptyToNull(ex.target_distance_meters_max),
    })),
  };
}

function emptyToNull(value) {
  if (value === '' || value == null) return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
}

export default function TemplateForm({
  defaultValues,
  onSubmit,
  onCancel,
  submitLabel = 'Save template',
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [serverError, setServerError] = useState(null);

  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(templateSchema),
    defaultValues,
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'exercises',
  });

  const handlePick = (exercise) => {
    append({
      exercise_id: exercise.id,
      name: exercise.name,
      muscle_group: exercise.muscle_group,
      primary_tracking_type: exercise.primary_tracking_type,
      secondary_tracking_types: exercise.secondary_tracking_types || [],
      target_sets: 3,
      target_reps_min: exercise.primary_tracking_type === 'reps' ? 8 : '',
      target_reps_max: exercise.primary_tracking_type === 'reps' ? 12 : '',
      target_duration_seconds_min: '',
      target_duration_seconds_max: '',
      target_distance_meters_min: '',
      target_distance_meters_max: '',
    });
  };

  const submit = async (values) => {
    setServerError(null);
    try {
      await onSubmit(toPayload(values));
    } catch (err) {
      setServerError(err?.message || 'Could not save the template.');
    }
  };

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

      <AppInput
        label="Template name"
        autoComplete="off"
        error={errors.name?.message}
        {...register('name')}
      />

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
              Add exercises and set targets. No weights — those come from Sessions.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {fields.map((field, index) => (
              <TemplateExerciseCard
                key={field.id}
                field={field}
                index={index}
                register={register}
                setValue={setValue}
                watch={watch}
                errors={errors.exercises?.[index]}
                onRemove={() => remove(index)}
              />
            ))}
          </div>
        )}

        {errors.exercises?.message || errors.exercises?.root?.message ? (
          <p className="text-sm font-medium text-destructive">
            {errors.exercises?.root?.message || errors.exercises?.message}
          </p>
        ) : null}

        <AppButton type="button" variant="outline" block onClick={() => setPickerOpen(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add exercise
        </AppButton>
      </section>

      <div className="flex flex-col gap-3 pt-2">
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
          selectedIds={fields.map((field) => Number(field.exercise_id))}
        />
      )}
    </form>
  );
}
