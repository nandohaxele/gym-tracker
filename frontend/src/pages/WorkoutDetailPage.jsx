import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  Pencil,
  Trash2,
  Loader2,
  AlertCircle,
  RotateCw,
  Dumbbell,
  Check,
} from 'lucide-react';

import { completeWorkout, deleteWorkout, getWorkout } from '@/api/workouts.js';
import useAsync from '@/hooks/useAsync.js';
import { formatDate } from '@/utils/format.js';
import { formatPlannedHint, formatSetLine } from '@/lib/tracking.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton, { buttonVariants } from '@/components/ui/AppButton.jsx';
import Modal from '@/components/ui/Modal.jsx';
import SaveAsTemplateDialog from '@/components/workouts/SaveAsTemplateDialog.jsx';
import { cn } from '@/lib/utils.js';

function ExerciseSection({ workoutExercise }) {
  const { exercise, sets = [] } = workoutExercise;
  const orderedSets = [...sets].sort((a, b) => a.order_index - b.order_index);
  const hint = formatPlannedHint(workoutExercise);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm">
      <div>
        <p className="font-semibold leading-tight">{exercise.name}</p>
        {exercise.muscle_group && (
          <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
            {exercise.muscle_group}
          </p>
        )}
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </div>

      {orderedSets.length > 0 ? (
        <ul className="flex flex-col gap-1.5">
          {orderedSets.map((set, index) => (
            <li
              key={set.id}
              className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2 text-sm"
            >
              <span className="font-medium text-muted-foreground">
                Set {index + 1}
              </span>
              <span className="font-semibold tabular-nums">
                {formatSetLine(set)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No sets logged yet.</p>
      )}
    </div>
  );
}

export default function WorkoutDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const { data: workout, error, loading, reload, setData } = useAsync(
    () => getWorkout(id),
    [id]
  );

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [actionError, setActionError] = useState(null);

  const handleDelete = async () => {
    setDeleting(true);
    setActionError(null);
    try {
      await deleteWorkout(id);
      navigate('/home', { replace: true });
    } catch (err) {
      setActionError(err?.message || 'Could not delete the workout.');
      setDeleting(false);
    }
  };

  const handleFinish = async () => {
    setFinishing(true);
    setActionError(null);
    try {
      const updated = await completeWorkout(id);
      setData(updated);
    } catch (err) {
      setActionError(err?.message || 'Could not finish the workout.');
    } finally {
      setFinishing(false);
    }
  };

  const orderedExercises = workout
    ? [...(workout.exercises || [])].sort((a, b) => a.order_index - b.order_index)
    : [];
  const isActive = workout?.ended_at == null;

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/home')}
          aria-label="Back to home"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      {loading ? (
        <StatusView
          icon={Loader2}
          spinIcon
          title="Loading workout…"
          description="Fetching the session details."
        />
      ) : error ? (
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
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">{workout.name}</h1>
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {isActive ? 'Active' : 'Completed'}
              </span>
            </div>
            <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" aria-hidden="true" />
              {formatDate(workout.date)}
            </p>
          </div>

          {actionError && (
            <p className="text-sm font-medium text-destructive">{actionError}</p>
          )}

          {isActive && (
            <AppButton block size="lg" loading={finishing} onClick={handleFinish}>
              <Check className="h-4 w-4" aria-hidden="true" />
              {finishing ? 'Finishing…' : 'Finish Workout'}
            </AppButton>
          )}

          <div className="flex gap-3">
            <Link
              to={`/workouts/${id}/edit`}
              className={cn(buttonVariants({ variant: 'outline' }), 'flex-1')}
            >
              <Pencil className="h-4 w-4" aria-hidden="true" />
              Edit
            </Link>
            <AppButton
              variant="destructive"
              className="flex-1"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Delete
            </AppButton>
          </div>

          <AppButton variant="ghost" block onClick={() => setSaveOpen(true)}>
            Save as My Template
          </AppButton>

          {orderedExercises.length > 0 ? (
            <div className="flex flex-col gap-3">
              {orderedExercises.map((we) => (
                <ExerciseSection key={we.id} workoutExercise={we} />
              ))}
            </div>
          ) : (
            <StatusView
              icon={Dumbbell}
              title="No exercises"
              description="This workout doesn't have any exercises yet."
            />
          )}
        </>
      )}

      <Modal
        open={confirmOpen}
        title="Delete workout?"
        onClose={() => (deleting ? null : setConfirmOpen(false))}
      >
        <div className="flex flex-col gap-4 p-4">
          <p className="text-sm text-muted-foreground">
            This permanently deletes “{workout?.name}” and all of its exercises and
            sets. This action can't be undone.
          </p>
          <AppButton
            variant="destructive"
            block
            loading={deleting}
            onClick={handleDelete}
          >
            {deleting ? 'Deleting…' : 'Delete workout'}
          </AppButton>
          <AppButton
            variant="ghost"
            block
            disabled={deleting}
            onClick={() => setConfirmOpen(false)}
          >
            Cancel
          </AppButton>
        </div>
      </Modal>

      {workout && (
        <SaveAsTemplateDialog
          open={saveOpen}
          workoutId={id}
          workoutName={workout.name}
          onClose={() => setSaveOpen(false)}
          onSaved={(template) => navigate(`/templates/${template.id}`)}
        />
      )}
    </PageContainer>
  );
}
