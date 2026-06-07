// HomePage - landing screen after auth. Fetches the workout history and renders
// it with loading / error / empty states. CTA to create a new workout.
// TODO (Phase 5 Step 3): swap the loading state for list skeletons.

import { Link } from 'react-router-dom';
import { Dumbbell, Plus, Loader2, AlertCircle, RotateCw } from 'lucide-react';

import useAuth from '@/hooks/useAuth.js';
import useAsync from '@/hooks/useAsync.js';
import { listWorkouts } from '@/api/workouts.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton, { buttonVariants } from '@/components/ui/AppButton.jsx';
import { cn } from '@/lib/utils.js';
import WorkoutList from '@/components/workouts/WorkoutList.jsx';

export default function HomePage() {
  const { user } = useAuth();
  const name = user?.email ? user.email.split('@')[0] : 'athlete';

  const { data: workouts, error, loading, reload } = useAsync(listWorkouts, []);

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Welcome back,</p>
          <h1 className="text-2xl font-bold capitalize tracking-tight">{name}</h1>
        </div>
        {workouts?.length > 0 && (
          <Link
            to="/workouts/new"
            className={cn(buttonVariants({ size: 'sm' }))}
            aria-label="New workout"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New
          </Link>
        )}
      </header>

      {loading ? (
        <StatusView
          icon={Loader2}
          spinIcon
          title="Loading workouts…"
          description="Fetching your training history."
        />
      ) : error ? (
        <StatusView
          icon={AlertCircle}
          tone="destructive"
          title="Couldn't load workouts"
          description={error}
        >
          <AppButton variant="outline" onClick={reload}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </AppButton>
        </StatusView>
      ) : workouts.length === 0 ? (
        <StatusView
          icon={Dumbbell}
          title="No workouts yet"
          description="Log your first session to start tracking your progress."
        >
          <Link to="/workouts/new" className={cn(buttonVariants({ size: 'lg' }), 'mt-1')}>
            <Plus className="h-5 w-5" aria-hidden="true" />
            New workout
          </Link>
        </StatusView>
      ) : (
        <WorkoutList workouts={workouts} />
      )}
    </PageContainer>
  );
}
