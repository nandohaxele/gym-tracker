import { Dumbbell, Loader2 } from 'lucide-react';

/**
 * LoadingScreen - full-viewport branded loader.
 * Shown while the auth state hydrates (e.g. validating a persisted token),
 * so we never flash protected content or the login page incorrectly.
 */
export default function LoadingScreen({ label = 'Loading…' }) {
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center gap-5 bg-background px-6"
      role="status"
      aria-live="polite"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Dumbbell className="h-8 w-8" aria-hidden="true" />
      </div>
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        <span className="text-sm font-medium">{label}</span>
      </div>
    </div>
  );
}
