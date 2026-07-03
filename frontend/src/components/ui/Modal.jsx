// Modal - mobile-first sheet, centered card on larger screens. Closes on
// backdrop click + Escape and locks body scroll while open.
//
// `anchor` controls the mobile position (desktop is always centered):
//   - 'bottom' (default): classic bottom sheet sliding up from the bottom.
//   - 'top': sheet pinned to the top of the viewport. Use for search-driven
//     content so the header/input stays put while the sheet grows/shrinks
//     downward with its results (collapsing bottom-up, keyboard-friendly).
//
// TODO (Phase 5 Step 3 polish): full focus trap + return-focus on close.

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils.js';

export default function Modal({
  open,
  onClose,
  title,
  children,
  className,
  anchor = 'bottom',
}) {
  useEffect(() => {
    if (!open) return undefined;

    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', onKeyDown);

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className={cn(
        'fixed inset-0 z-50 flex justify-center sm:items-center',
        anchor === 'top' ? 'items-start' : 'items-end'
      )}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      <div
        className={cn(
          'relative flex max-h-[85dvh] w-full max-w-md flex-col overflow-hidden',
          'border border-border bg-card shadow-2xl animate-scale-in sm:rounded-2xl',
          anchor === 'top'
            ? 'rounded-b-2xl pt-safe sm:pt-0'
            : 'rounded-t-2xl pb-safe',
          className
        )}
      >
        <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
