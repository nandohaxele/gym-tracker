// WorkoutEditorPage - placeholder for Phase 5 Step 2.
// TODO: build the create/edit workout flow:
//   - workout name + date
//   - add exercises (ExercisePicker) with nested sets (reps / weight)
//   - submit via api/workouts.createWorkout / updateWorkout
//   - reuse the same form for /workouts/new and /workouts/:id/edit

import { useNavigate } from 'react-router-dom';
import { Hammer, ArrowLeft } from 'lucide-react';
import PageContainer from '@/components/ui/PageContainer.jsx';
import AppButton from '@/components/ui/AppButton.jsx';

export default function WorkoutEditorPage() {
  const navigate = useNavigate();

  return (
    <PageContainer className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">New workout</h1>

      <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border bg-card/50 px-6 py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Hammer className="h-7 w-7" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Workout editor coming soon</h2>
          <p className="text-sm text-muted-foreground">
            This is where you'll build a session with exercises and sets.
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
