// ExerciseFieldCard - one exercise block inside the workout editor.
// Owns its own nested field array of sets (react-hook-form), so adding/removing
// sets stays local and we avoid lifting set state up to the form.

import { useFieldArray } from 'react-hook-form';
import { Plus, X } from 'lucide-react';
import AppButton from '@/components/ui/AppButton.jsx';
import SetRow from './SetRow.jsx';

const newSet = () => ({ reps: '', weight: '' });

export default function ExerciseFieldCard({
  control,
  register,
  exerciseIndex,
  field,
  errors,
  onRemove,
}) {
  const { fields, append, remove } = useFieldArray({
    control,
    name: `exercises.${exerciseIndex}.sets`,
  });

  const setsError = errors?.sets;
  // useFieldArray-level message (e.g. "Add at least one set") lives on `.root`.
  const setsRootMessage = setsError?.root?.message || setsError?.message;

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

      {fields.length > 0 && (
        <div className="flex items-center gap-2 pl-7 pr-9 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          <span className="flex-1 text-center">Reps</span>
          <span className="flex-1 text-center">Weight</span>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {fields.map((setField, setIndex) => (
          <SetRow
            key={setField.id}
            index={setIndex}
            baseName={`exercises.${exerciseIndex}.sets.${setIndex}`}
            register={register}
            errors={setsError?.[setIndex]}
            onRemove={() => remove(setIndex)}
            canRemove={fields.length > 1}
          />
        ))}
      </div>

      {setsRootMessage && (
        <p className="text-xs font-medium text-destructive">{setsRootMessage}</p>
      )}

      <AppButton
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => append(newSet())}
        className="self-start"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        Add set
      </AppButton>
    </div>
  );
}
