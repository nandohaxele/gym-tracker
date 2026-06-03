import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * cn - merge conditional class names and de-duplicate conflicting Tailwind
 * utilities (e.g. `cn('p-2', condition && 'p-4')` -> `p-4`).
 * This is the standard shadcn/ui class helper.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
