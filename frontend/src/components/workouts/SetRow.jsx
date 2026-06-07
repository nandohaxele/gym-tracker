// SetRow - inline editor for a single set (reps + weight + delete).
// Integrates with react-hook-form via `register`; validation comes from the
// shared workoutSchema. Inputs are numeric-keyboard friendly and >=44px tall.

import { Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils.js';

const fieldClass =
  'h-11 w-full rounded-lg border bg-background px-3 text-center text-base text-foreground ' +
  'transition-colors placeholder:text-muted-foreground ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background';

export default function SetRow({
  index,
  baseName,
  register,
  errors,
  onRemove,
  canRemove = true,
}) {
  const errorMessage = errors?.reps?.message || errors?.weight?.message;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="w-5 shrink-0 text-center text-sm font-semibold text-muted-foreground">
          {index + 1}
        </span>

        <input
          type="number"
          inputMode="numeric"
          min="1"
          step="1"
          placeholder="Reps"
          aria-label={`Set ${index + 1} reps`}
          aria-invalid={errors?.reps ? 'true' : undefined}
          className={cn(fieldClass, 'flex-1', errors?.reps ? 'border-destructive' : 'border-input')}
          {...register(`${baseName}.reps`)}
        />

        <input
          type="number"
          inputMode="decimal"
          min="0"
          step="0.5"
          placeholder="kg"
          aria-label={`Set ${index + 1} weight`}
          aria-invalid={errors?.weight ? 'true' : undefined}
          className={cn(fieldClass, 'flex-1', errors?.weight ? 'border-destructive' : 'border-input')}
          {...register(`${baseName}.weight`)}
        />

        <button
          type="button"
          onClick={onRemove}
          disabled={!canRemove}
          aria-label={`Remove set ${index + 1}`}
          className="inline-flex h-11 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:text-destructive disabled:pointer-events-none disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {errorMessage && (
        <p className="pl-7 text-xs font-medium text-destructive">{errorMessage}</p>
      )}
    </div>
  );
}
