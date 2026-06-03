// HomePage - landing screen after auth.
// Phase 5 Step 1: greets the user + shows a polished empty state.
// TODO (Phase 5 Step 2): fetch workouts via api/workouts.listWorkouts and
//   render <WorkoutList /> with loading / error / empty states.

import { Link } from 'react-router-dom';
import { Dumbbell, Plus } from 'lucide-react';
import useAuth from '@/hooks/useAuth.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import { buttonVariants } from '@/components/ui/AppButton.jsx';
import { cn } from '@/lib/utils.js';

export default function HomePage() {
  const { user } = useAuth();
  const name = user?.email ? user.email.split('@')[0] : 'athlete';

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">Welcome back,</p>
        <h1 className="text-2xl font-bold capitalize tracking-tight">{name}</h1>
      </header>

      {/* Empty state placeholder until the workout list is wired up. */}
      <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Dumbbell className="h-7 w-7" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">No workouts yet</h2>
          <p className="text-sm text-muted-foreground">
            Log your first session to start tracking your progress.
          </p>
        </div>
        <Link
          to="/workouts/new"
          className={cn(buttonVariants({ size: 'lg' }), 'mt-1')}
        >
          <Plus className="h-5 w-5" aria-hidden="true" />
          New workout
        </Link>
      </div>
    </PageContainer>
  );
}
