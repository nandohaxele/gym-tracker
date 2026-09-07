// SetRow - tracking-aware inline editor for one Set or client draft.
// Drafts have no set_id and are not persisted until the primary metric is set.

import { Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils.js';
import {
  kmInputToMeters,
  metersToKmInput,
  partsToSeconds,
  secondsToParts,
} from '@/utils/format.js';
import { showsField } from '@/lib/tracking.js';

const fieldClass =
          'h-11 w-full min-w-[3.25rem] rounded-lg border bg-background px-2 text-center text-base text-foreground ' +
  'transition-colors placeholder:text-muted-foreground ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background';

function NumberField({
  label,
  value,
  onChange,
  onCommit,
  min,
  step = '1',
  inputMode = 'numeric',
  placeholder,
  className,
}) {
  return (
    <input
      type="number"
      inputMode={inputMode}
      min={min}
      step={step}
      placeholder={placeholder || label}
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={onCommit}
      className={cn(fieldClass, 'flex-1', className)}
    />
  );
}

export default function SetRow({
  index,
  row,
  tracking,
  onChange,
  onCommit,
  onRemove,
  canRemove = true,
  busy = false,
}) {
  const duration = secondsToParts(row.duration_seconds);
  const setDuration = (minutes, seconds) => {
    onChange({ duration_seconds: partsToSeconds(minutes, seconds) ?? '' });
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <span className="w-5 shrink-0 text-center text-sm font-semibold text-muted-foreground">
          {index + 1}
        </span>

        {showsField(tracking, 'reps') && (
          <NumberField
            label={`Set ${index + 1} reps`}
            value={row.reps}
            min="1"
            placeholder="Reps"
            onChange={(reps) => onChange({ reps })}
            onCommit={onCommit}
          />
        )}

        {showsField(tracking, 'duration') && (
          <div className="flex min-w-[9rem] flex-1 items-center gap-1">
            <NumberField
              label={`Set ${index + 1} minutes`}
              value={duration.minutes}
              min="0"
              placeholder="min"
              onChange={(minutes) => setDuration(minutes, duration.seconds)}
              onCommit={onCommit}
            />
            <NumberField
              label={`Set ${index + 1} seconds`}
              value={duration.seconds}
              min="0"
              placeholder="sec"
              onChange={(seconds) => setDuration(duration.minutes, seconds)}
              onCommit={onCommit}
            />
          </div>
        )}

        {showsField(tracking, 'distance') && (
          <NumberField
            label={`Set ${index + 1} distance (km)`}
            value={metersToKmInput(row.distance_meters)}
            min="0"
            step="0.01"
            inputMode="decimal"
            placeholder="km"
            onChange={(km) =>
              onChange({ distance_meters: kmInputToMeters(km) ?? '' })
            }
            onCommit={onCommit}
          />
        )}

        <NumberField
          label={`Set ${index + 1} weight (kg)`}
          value={row.weight_kg}
          min="0"
          step="0.5"
          inputMode="decimal"
          placeholder="kg"
          onChange={(weight_kg) => onChange({ weight_kg })}
          onCommit={onCommit}
        />

        <button
          type="button"
          onClick={onRemove}
          disabled={!canRemove || busy}
          aria-label={`Remove set ${index + 1}`}
          className="inline-flex h-11 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:text-destructive disabled:pointer-events-none disabled:opacity-30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Trash2 className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
