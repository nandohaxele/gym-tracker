// WorkoutEditorPage - create (/workouts/new) and edit (/workouts/:id/edit).
// In edit mode it loads the existing workout and hydrates the form; both modes
// share <WorkoutForm />.

import { useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle, RotateCw } from 'lucide-react';

import { getWorkout, createWorkout, updateWorkout } from '@/api/workouts.js';
import useAsync from '@/hooks/useAsync.js';
import { toDateInputValue } from '@/utils/format.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton from '@/components/ui/AppButton.jsx';
import WorkoutForm from '@/components/workouts/WorkoutForm.jsx';

// Map a backend workout detail into the shape WorkoutForm expects.
function mapWorkoutToForm(workout) {
  const exercises = [...(workout.exercises || [])]
    .sort((a, b) => a.order_index - b.order_index)
    .map((we) => ({
      exercise_id: we.exercise.id,
      name: we.exercise.name,
      muscle_group: we.exercise.muscle_group,
      sets: [...(we.sets || [])]
        .sort((a, b) => a.order_index - b.order_index)
        .map((s) => ({ reps: s.reps, weight: s.weight })),
    }));

  return {
    name: workout.name,
    date: toDateInputValue(workout.date),
    exercises,
  };
}

export default function WorkoutEditorPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);

  const fetcher = useCallback(
    () => (isEdit ? getWorkout(id) : Promise.resolve(null)),
    [id, isEdit]
  );
  const { data: workout, error, loading, reload } = useAsync(fetcher, [id]);

  const handleSubmit = async (payload) => {
    if (isEdit) {
      await updateWorkout(id, payload);
      navigate(`/workouts/${id}`, { replace: true });
    } else {
      const created = await createWorkout(payload);
      navigate(`/workouts/${created.id}`, { replace: true });
    }
  };

  const handleCancel = () => {
    if (isEdit) navigate(`/workouts/${id}`);
    else navigate('/home');
  };

  const defaultValues = isEdit
    ? workout && mapWorkoutToForm(workout)
    : { name: '', date: toDateInputValue(), exercises: [] };

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleCancel}
          aria-label="Back"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
        <h1 className="text-2xl font-bold tracking-tight">
          {isEdit ? 'Edit workout' : 'New workout'}
        </h1>
      </header>

      {isEdit && loading ? (
        <StatusView
          icon={Loader2}
          spinIcon
          title="Loading workout…"
          description="Fetching the session details."
        />
      ) : isEdit && error ? (
        <StatusView
          icon={AlertCircle}
          tone="destructive"
          title="Couldn't load workout"
          description={error}
        >
          <AppButton variant="outline" onClick={reload}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </AppButton>
        </StatusView>
      ) : defaultValues ? (
        <WorkoutForm
          defaultValues={defaultValues}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          submitLabel={isEdit ? 'Save changes' : 'Create workout'}
        />
      ) : null}
    </PageContainer>
  );
}
