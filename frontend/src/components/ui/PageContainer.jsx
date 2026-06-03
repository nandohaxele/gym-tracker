import { cn } from '@/lib/utils.js';

/**
 * PageContainer - mobile-first content wrapper.
 * Caps the reading width (phone-like even on desktop) and applies consistent
 * horizontal padding. Use inside AppShell's content area or standalone pages.
 */
export default function PageContainer({ className, children, ...props }) {
  return (
    <div
      className={cn('mx-auto w-full max-w-md px-4', className)}
      {...props}
    >
      {children}
    </div>
  );
}
