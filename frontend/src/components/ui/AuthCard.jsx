import { Dumbbell } from 'lucide-react';
import { cn } from '@/lib/utils.js';

/**
 * AuthCard - polished card wrapper for the login / register screens.
 * Renders the brand mark, a title + subtitle, the form (children), and an
 * optional footer (e.g. "New here? Create an account").
 */
export default function AuthCard({ title, subtitle, children, footer, className }) {
  return (
    <div
      className={cn(
        'w-full rounded-2xl border border-border bg-card p-6 shadow-xl shadow-black/5 animate-scale-in sm:p-8',
        className
      )}
    >
      <div className="mb-7 flex flex-col items-center text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
          <Dumbbell className="h-7 w-7" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
        {subtitle && (
          <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>

      {children}

      {footer && (
        <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>
      )}
    </div>
  );
}
