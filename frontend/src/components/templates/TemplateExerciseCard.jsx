import { X } from 'lucide-react';
import AppInput from '@/components/ui/AppInput.jsx';
import { kmInputToMeters, metersToKmInput, partsToSeconds, secondsToParts } from '@/utils/format.js';
import { trackingOf } from '@/lib/tracking.js';

export default function TemplateExerciseCard({
  field,
  register,
  setValue,
  watch,
  errors,
  onRemove,
  index,
}) {
  const tracking = trackingOf(field);
  const prefix = `exercises.${index}`;
  const durationMin = secondsToParts(watch(`${prefix}.target_duration_seconds_min`));
  const durationMax = secondsToParts(watch(`${prefix}.target_duration_seconds_max`));

  const setDurationPair = (which, minutes, seconds) => {
    setValue(`${prefix}.target_duration_seconds_${which}`, partsToSeconds(minutes, seconds) ?? '', {
      shouldValidate: true,
    });
  };

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-semibold leading-tight">{field.name}</p>
          {field.muscle_group && (
            <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
              {field.muscle_group}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${field.name || 'exercise'}`}
          className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <AppInput
        label="Target sets"
        type="number"
        inputMode="numeric"
        min="1"
        error={errors?.target_sets?.message}
        {...register(`${prefix}.target_sets`)}
      />

      {tracking.primary === 'reps' || tracking.secondaries.includes('reps') ? (
        <div className="grid grid-cols-2 gap-2">
          <AppInput
            label="Reps min"
            type="number"
            inputMode="numeric"
            min="1"
            error={errors?.target_reps_min?.message}
            {...register(`${prefix}.target_reps_min`)}
          />
          <AppInput
            label="Reps max"
            type="number"
            inputMode="numeric"
            min="1"
            error={errors?.target_reps_max?.message}
            {...register(`${prefix}.target_reps_max`)}
          />
        </div>
      ) : null}

      {tracking.primary === 'duration' || tracking.secondaries.includes('duration') ? (
        <div className="grid grid-cols-2 gap-2">
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">Duration min</p>
            <div className="flex gap-2">
              <AppInput
                type="number"
                inputMode="numeric"
                min="0"
                placeholder="min"
                value={durationMin.minutes}
                onChange={(e) =>
                  setDurationPair('min', e.target.value, durationMin.seconds)
                }
              />
              <AppInput
                type="number"
                inputMode="numeric"
                min="0"
                placeholder="sec"
                value={durationMin.seconds}
                onChange={(e) =>
                  setDurationPair('min', durationMin.minutes, e.target.value)
                }
              />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">Duration max</p>
            <div className="flex gap-2">
              <AppInput
                type="number"
                inputMode="numeric"
                min="0"
                placeholder="min"
                value={durationMax.minutes}
                onChange={(e) =>
                  setDurationPair('max', e.target.value, durationMax.seconds)
                }
              />
              <AppInput
                type="number"
                inputMode="numeric"
                min="0"
                placeholder="sec"
                value={durationMax.seconds}
                onChange={(e) =>
                  setDurationPair('max', durationMax.minutes, e.target.value)
                }
              />
            </div>
            {errors?.target_duration_seconds_min?.message && (
              <p className="text-sm font-medium text-destructive">
                {errors.target_duration_seconds_min.message}
              </p>
            )}
          </div>
        </div>
      ) : null}

      {tracking.primary === 'distance' || tracking.secondaries.includes('distance') ? (
        <div className="grid grid-cols-2 gap-2">
          <AppInput
            label="Distance min (km)"
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            error={errors?.target_distance_meters_min?.message}
            value={metersToKmInput(watch(`${prefix}.target_distance_meters_min`))}
            onChange={(e) =>
              setValue(
                `${prefix}.target_distance_meters_min`,
                kmInputToMeters(e.target.value) ?? '',
                { shouldValidate: true }
              )
            }
          />
          <AppInput
            label="Distance max (km)"
            type="number"
            inputMode="decimal"
            min="0"
            step="0.01"
            error={errors?.target_distance_meters_max?.message}
            value={metersToKmInput(watch(`${prefix}.target_distance_meters_max`))}
            onChange={(e) =>
              setValue(
                `${prefix}.target_distance_meters_max`,
                kmInputToMeters(e.target.value) ?? '',
                { shouldValidate: true }
              )
            }
          />
        </div>
      ) : null}
    </div>
  );
}
