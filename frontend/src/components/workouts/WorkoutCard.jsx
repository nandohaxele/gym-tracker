// WorkoutCard - one tappable row in the history list. Large hit area, links to
// the workout detail. The list endpoint returns a summary (id, name, date), so
// we keep the card to name + formatted date.

import { Link } from 'react-router-dom';
import { Calendar, ChevronRight } from 'lucide-react';
import { formatDate } from '@/utils/format.js';

export default function WorkoutCard({ workout }) {
  return (
    <Link
      to={`/workouts/${workout.id}`}
      className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-4 shadow-sm transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background active:scale-[0.99]"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold leading-tight">{workout.name}</p>
        <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground">
          <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
          {formatDate(workout.date)}
        </p>
      </div>
      <ChevronRight
        className="h-5 w-5 shrink-0 text-muted-foreground"
        aria-hidden="true"
      />
    </Link>
  );
}
