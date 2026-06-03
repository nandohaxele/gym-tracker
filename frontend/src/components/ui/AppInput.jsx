import { forwardRef, useId } from 'react';
import { cn } from '@/lib/utils.js';
import Label from './Label.jsx';

/**
 * AppInput - labelled text input with inline error + optional icons.
 * forwardRef so it plugs straight into react-hook-form's `register`.
 *
 * Props:
 *   label      - visible field label
 *   error      - error message string (renders red + aria-invalid)
 *   hint       - small helper text shown when there is no error
 *   leftIcon   - node rendered inside the field on the left
 *   rightSlot  - node rendered inside the field on the right (e.g. show/hide)
 */
const AppInput = forwardRef(function AppInput(
  { label, error, hint, leftIcon, rightSlot, className, id, ...props },
  ref
) {
  const autoId = useId();
  const inputId = id || props.name || autoId;
  const describedById = error
    ? `${inputId}-error`
    : hint
      ? `${inputId}-hint`
      : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      {label && <Label htmlFor={inputId}>{label}</Label>}

      <div className="relative">
        {leftIcon && (
          <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
            {leftIcon}
          </span>
        )}

        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={describedById}
          className={cn(
            'flex h-12 w-full rounded-lg border bg-background px-3.5 text-base text-foreground',
            'transition-colors placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
            'disabled:cursor-not-allowed disabled:opacity-50',
            leftIcon && 'pl-10',
            rightSlot && 'pr-11',
            error ? 'border-destructive focus-visible:ring-destructive' : 'border-input',
            className
          )}
          {...props}
        />

        {rightSlot && (
          <span className="absolute inset-y-0 right-0 flex items-center pr-2">
            {rightSlot}
          </span>
        )}
      </div>

      {error ? (
        <p id={`${inputId}-error`} className="text-sm font-medium text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
});

export default AppInput;
