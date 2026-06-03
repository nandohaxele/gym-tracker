// WorkoutDetailPage - placeholder for Phase 5 Step 2.
// TODO: fetch the workout via api/workouts.getWorkout(id) and render the full
//   nested detail (exercises + sets), with edit / delete actions.

import { useNavigate, useParams } from 'react-router-dom';
import { ClipboardList, ArrowLeft } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer.jsx';
import AppButton from '@/components/ui/AppButton.jsx';

export default function WorkoutDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  return (
    <PageContainer className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">Workout #{id}</h1>

      <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <ClipboardList className="h-7 w-7" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Workout detail coming soon</h2>
          <p className="text-sm text-muted-foreground">
            Exercises and sets for this session will appear here.
          </p>
        </div>
        <AppButton variant="outline" onClick={() => navigate('/home')}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to home
        </AppButton>
      </div>
    </PageContainer>
  );
}
