import { cn } from '@/lib/utils.js';

/**
 * StatusView - reusable centered state block for loading / empty / error
 * screens. Mirrors the polished dashed-card empty state used across the app.
 *
 * Props:
 *   icon        - lucide icon component (rendered inside a tinted badge)
 *   title       - bold headline
 *   description - muted supporting copy
 *   tone        - 'default' | 'destructive' (tints the icon badge)
 *   spinIcon    - spin the icon (handy for a Loader2 loading state)
 *   children    - optional actions (buttons / links) rendered below the copy
 */
export default function StatusView({
  icon: Icon,
  title,
  description,
  tone = 'default',
  spinIcon = false,
  children,
  className,
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-12 text-center',
        className
      )}
    >
      {Icon && (
        <div
          className={cn(
            'flex h-14 w-14 items-center justify-center rounded-2xl',
            tone === 'destructive'
              ? 'bg-destructive/10 text-destructive'
              : 'bg-primary/10 text-primary'
          )}
        >
          <Icon
            className={cn('h-7 w-7', spinIcon && 'animate-spin')}
            aria-hidden="true"
          />
        </div>
      )}

      <div className="space-y-1">
        {title && <h2 className="text-lg font-semibold">{title}</h2>}
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>

      {children}
    </div>
  );
}
