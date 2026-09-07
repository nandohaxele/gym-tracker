// HomePage - landing screen after auth. Fetches the workout history and renders
// it with loading / error / empty states. CTA to create a new workout.

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Dumbbell, Mic, Plus, Loader2, AlertCircle, RotateCw } from 'lucide-react';

import useAuth from '@/hooks/useAuth.js';
import useAsync from '@/hooks/useAsync.js';
import { listWorkouts } from '@/api/workouts.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton, { buttonVariants } from '@/components/ui/AppButton.jsx';
import VoiceAssistantSheet from '@/components/assistant/VoiceAssistantSheet.jsx';
import { createdWorkoutId } from '@/lib/assistant.js';
import { cn } from '@/lib/utils.js';
import WorkoutList from '@/components/workouts/WorkoutList.jsx';

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const name = user?.email ? user.email.split('@')[0] : 'athlete';
  const [assistantOpen, setAssistantOpen] = useState(false);

  const { data: workouts, error, loading, reload } = useAsync(listWorkouts, []);

  const handleAssistantExecuted = (executeResult) => {
    const created = createdWorkoutId(executeResult);
    if (created) {
      navigate(`/workouts/${created}/edit`, { replace: true });
      return;
    }
    reload();
  };

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Welcome back Soldier!</p>
          <h1 className="text-2xl font-bold capitalize tracking-tight">{name}</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setAssistantOpen(true)}
            aria-label="Voice assistant"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Mic className="h-5 w-5" aria-hidden="true" />
          </button>
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
        </div>
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
      ) : (workouts ?? []).length === 0 ? (
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

      <VoiceAssistantSheet
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
        onExecuted={handleAssistantExecuted}
      />
    </PageContainer>
  );
}
