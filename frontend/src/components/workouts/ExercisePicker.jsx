// ExercisePicker - modal that lists the seeded exercise catalog, grouped by
// muscle group, with a case-insensitive search. Picking an exercise calls
// onPick(exercise) and closes the sheet.
//
// Mount this only while open (the parent conditionally renders it) so the
// catalog fetch runs fresh each time it's opened.

import { useMemo, useState } from 'react';
import { AlertCircle, Check, Loader2, Search } from 'lucide-react';
import { listExercises } from '@/api/exercises.js';
import useAsync from '@/hooks/useAsync.js';
import Modal from '@/components/ui/Modal.jsx';

export default function ExercisePicker({ onPick, onClose, selectedIds = [] }) {
  const { data: exercises, error, loading } = useAsync(listExercises, []);
  const [query, setQuery] = useState('');

  const groups = useMemo(() => {
    const list = exercises || [];
    const q = query.trim().toLowerCase();
    const filtered = q
      ? list.filter(
          (ex) =>
            ex.name.toLowerCase().includes(q) ||
            ex.muscle_group.toLowerCase().includes(q)
        )
      : list;

    const byGroup = new Map();
    for (const ex of filtered) {
      const key = ex.muscle_group || 'Other';
      if (!byGroup.has(key)) byGroup.set(key, []);
      byGroup.get(key).push(ex);
    }
    return [...byGroup.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([group, items]) => [
        group,
        items.sort((a, b) => a.name.localeCompare(b.name)),
      ]);
  }, [exercises, query]);

  const selected = new Set(selectedIds);

  return (
    // Fixed (dvh-based) height keeps the sheet from collapsing to the size of a
    // short result list and adapts when the Android keyboard shrinks the
    // viewport -- the sticky search + first match stay anchored at the top.
    <Modal open title="Add exercise" onClose={onClose} className="h-[85dvh]">
      <div className="flex min-h-full flex-col">
        <div className="sticky top-0 z-10 border-b border-border bg-card p-4">
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-muted-foreground">
              <Search className="h-4 w-4" aria-hidden="true" />
            </span>
            <input
              type="search"
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search exercises…"
              aria-label="Search exercises"
              className="h-12 w-full rounded-lg border border-input bg-background pl-10 pr-3.5 text-base text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            />
          </div>
        </div>

        <div className="p-4">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span className="text-sm">Loading exercises…</span>
            </div>
          ) : error ? (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : groups.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No exercises match “{query}”.
            </p>
          ) : (
            <div className="flex flex-col gap-5">
              {groups.map(([group, items]) => (
                <div key={group} className="flex flex-col gap-1.5">
                  <p className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {group}
                  </p>
                  <ul className="flex flex-col gap-1">
                    {items.map((ex) => {
                      const isSelected = selected.has(ex.id);
                      return (
                        <li key={ex.id}>
                          <button
                            type="button"
                            onClick={() => {
                              onPick?.(ex);
                              onClose?.();
                            }}
                            className="flex w-full items-center justify-between gap-2 rounded-lg border border-transparent px-3 py-3 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            <span className="font-medium">{ex.name}</span>
                            {isSelected && (
                              <span className="flex items-center gap-1 text-xs font-medium text-primary">
                                <Check className="h-3.5 w-3.5" aria-hidden="true" />
                                Added
                              </span>
                            )}
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
