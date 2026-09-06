import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle } from 'lucide-react';

import { createExercise } from '@/api/exercises.js';
import { personalExerciseSchema } from '@/lib/validators.js';
import { TRACKING_TYPES } from '@/lib/tracking.js';
import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';

const LABELS = {
  reps: 'Reps',
  duration: 'Duration',
  distance: 'Distance',
};

export default function CreateExerciseForm({ onCreated, onCancel, muscleGroups = [] }) {
  const [serverError, setServerError] = useState(null);
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(personalExerciseSchema),
    defaultValues: {
      name: '',
      primary_tracking_type: 'reps',
      secondary_tracking_types: [],
      muscle_group: '',
    },
  });

  const primary = watch('primary_tracking_type');
  const secondaries = watch('secondary_tracking_types') || [];

  const toggleSecondary = (type) => {
    const next = secondaries.includes(type)
      ? secondaries.filter((item) => item !== type)
      : [...secondaries, type];
    setValue('secondary_tracking_types', next, { shouldValidate: true });
  };

  const submit = async (values) => {
    setServerError(null);
    try {
      const created = await createExercise({
        name: values.name.trim(),
        primary_tracking_type: values.primary_tracking_type,
        secondary_tracking_types: (values.secondary_tracking_types || []).filter(
          (type) => type !== values.primary_tracking_type
        ),
        muscle_group: values.muscle_group || null,
      });
      onCreated?.(created);
    } catch (err) {
      setServerError(err?.message || 'Could not create the exercise.');
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-4 p-4">
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
        label="Name"
        placeholder="e.g. Cable crunch"
        autoComplete="off"
        error={errors.name?.message}
        {...register('name')}
      />

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Primary tracking</legend>
        <div className="flex flex-wrap gap-2">
          {TRACKING_TYPES.map((type) => (
            <label
              key={type}
              className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-input px-3 text-sm"
            >
              <input
                type="radio"
                value={type}
                {...register('primary_tracking_type')}
              />
              {LABELS[type]}
            </label>
          ))}
        </div>
        {errors.primary_tracking_type?.message && (
          <p className="text-sm font-medium text-destructive">
            {errors.primary_tracking_type.message}
          </p>
        )}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-medium">Optional extras</legend>
        <div className="flex flex-wrap gap-2">
          {TRACKING_TYPES.filter((type) => type !== primary).map((type) => (
            <label
              key={type}
              className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-input px-3 text-sm"
            >
              <input
                type="checkbox"
                checked={secondaries.includes(type)}
                onChange={() => toggleSecondary(type)}
              />
              {LABELS[type]}
            </label>
          ))}
        </div>
      </fieldset>

      <AppInput
        label="Muscle group (optional)"
        placeholder="Leave empty if unclassified"
        autoComplete="off"
        list="muscle-group-suggestions"
        error={errors.muscle_group?.message}
        {...register('muscle_group')}
      />
      <datalist id="muscle-group-suggestions">
        {muscleGroups.map((group) => (
          <option key={group} value={group} />
        ))}
      </datalist>

      <div className="flex flex-col gap-3 pt-1">
        <AppButton type="submit" block loading={isSubmitting}>
          {isSubmitting ? 'Creating…' : 'Create exercise'}
        </AppButton>
        <AppButton type="button" variant="ghost" block onClick={onCancel}>
          Back to catalog
        </AppButton>
      </div>
    </form>
  );
}
