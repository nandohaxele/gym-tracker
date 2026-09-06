import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Loader2,
  AlertCircle,
  RotateCw,
  Play,
  Pencil,
  Trash2,
  Copy,
} from 'lucide-react';

import { deleteTemplate, getTemplate, personalizeTemplate, startTemplate } from '@/api/templates.js';
import useAsync from '@/hooks/useAsync.js';
import { formatDistance, formatDuration } from '@/utils/format.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton, { buttonVariants } from '@/components/ui/AppButton.jsx';
import Modal from '@/components/ui/Modal.jsx';
import AppInput from '@/components/ui/AppInput.jsx';
import { cn } from '@/lib/utils.js';

function targetLine(ex) {
  const parts = [`${ex.target_sets} sets`];
  if (ex.target_reps_min != null) {
    parts.push(
      ex.target_reps_min === ex.target_reps_max
        ? `${ex.target_reps_min} reps`
        : `${ex.target_reps_min}–${ex.target_reps_max} reps`
    );
  }
  if (ex.target_duration_seconds_min != null) {
    parts.push(
      ex.target_duration_seconds_min === ex.target_duration_seconds_max
        ? formatDuration(ex.target_duration_seconds_min)
        : `${formatDuration(ex.target_duration_seconds_min)}–${formatDuration(ex.target_duration_seconds_max)}`
    );
  }
  if (ex.target_distance_meters_min != null) {
    parts.push(
      ex.target_distance_meters_min === ex.target_distance_meters_max
        ? formatDistance(ex.target_distance_meters_min)
        : `${formatDistance(ex.target_distance_meters_min)}–${formatDistance(ex.target_distance_meters_max)}`
    );
  }
  return parts.join(' · ');
}

export default function TemplateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: template, error, loading, reload } = useAsync(() => getTemplate(id), [id]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [personalizeOpen, setPersonalizeOpen] = useState(false);
  const [copyName, setCopyName] = useState('');

  const handleStart = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const workout = await startTemplate(id);
      navigate(`/workouts/${workout.id}/edit`);
    } catch (err) {
      setActionError(err?.message || 'Could not start the template.');
      setBusy(false);
    }
  };

  const handlePersonalize = async () => {
    setBusy(true);
    setActionError(null);
    try {
      const copy = await personalizeTemplate(id, copyName.trim() || undefined);
      navigate(`/templates/${copy.id}/edit`);
    } catch (err) {
      setActionError(err?.message || 'Could not personalize the template.');
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    setBusy(true);
    setActionError(null);
    try {
      await deleteTemplate(id);
      navigate('/templates', { replace: true });
    } catch (err) {
      setActionError(err?.message || 'Could not delete the template.');
      setBusy(false);
    }
  };

  const exercises = template
    ? [...(template.exercises || [])].sort((a, b) => a.order_index - b.order_index)
    : [];

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/templates')}
          aria-label="Back to templates"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      {loading ? (
        <StatusView icon={Loader2} spinIcon title="Loading template…" />
      ) : error ? (
        <StatusView icon={AlertCircle} tone="destructive" title="Couldn't load template" description={error}>
          <AppButton variant="outline" onClick={reload}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </AppButton>
        </StatusView>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold tracking-tight">{template.name}</h1>
            <p className="text-sm text-muted-foreground">
              {template.is_global ? 'Global template' : 'My template'}
            </p>
          </div>

          {actionError && (
            <p className="text-sm font-medium text-destructive">{actionError}</p>
          )}

          <div className="flex flex-col gap-3">
            <AppButton block size="lg" disabled={busy} onClick={handleStart}>
              <Play className="h-4 w-4" aria-hidden="true" />
              Start
            </AppButton>
            {template.is_global ? (
              <AppButton
                variant="outline"
                block
                disabled={busy}
                onClick={() => {
                  setCopyName(template.name);
                  setPersonalizeOpen(true);
                }}
              >
                <Copy className="h-4 w-4" aria-hidden="true" />
                Personalize
              </AppButton>
            ) : (
              <div className="flex gap-3">
                <Link
                  to={`/templates/${id}/edit`}
                  className={cn(buttonVariants({ variant: 'outline' }), 'flex-1')}
                >
                  <Pencil className="h-4 w-4" aria-hidden="true" />
                  Edit
                </Link>
                <AppButton
                  variant="destructive"
                  className="flex-1"
                  disabled={busy}
                  onClick={() => setConfirmOpen(true)}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  Delete
                </AppButton>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-3">
            {exercises.map((ex) => (
              <div
                key={ex.id}
                className="rounded-2xl border border-border bg-card p-4 shadow-sm"
              >
                <p className="font-semibold">{ex.exercise.name}</p>
                {ex.exercise.muscle_group && (
                  <p className="mt-0.5 text-xs uppercase tracking-wide text-muted-foreground">
                    {ex.exercise.muscle_group}
                  </p>
                )}
                <p className="mt-2 text-sm text-muted-foreground">{targetLine(ex)}</p>
              </div>
            ))}
          </div>
        </>
      )}

      <Modal
        open={confirmOpen}
        title="Delete template?"
        onClose={() => (busy ? null : setConfirmOpen(false))}
      >
        <div className="flex flex-col gap-4 p-4">
          <p className="text-sm text-muted-foreground">
            Started Sessions keep their planned snapshot. This cannot be undone.
          </p>
          <AppButton variant="destructive" block loading={busy} onClick={handleDelete}>
            Delete template
          </AppButton>
          <AppButton variant="ghost" block disabled={busy} onClick={() => setConfirmOpen(false)}>
            Cancel
          </AppButton>
        </div>
      </Modal>

      <Modal
        open={personalizeOpen}
        title="Personalize template"
        onClose={() => (busy ? null : setPersonalizeOpen(false))}
      >
        <div className="flex flex-col gap-4 p-4">
          <AppInput
            label="Name"
            value={copyName}
            onChange={(e) => setCopyName(e.target.value)}
          />
          <AppButton block loading={busy} onClick={handlePersonalize}>
            Create My Template
          </AppButton>
          <AppButton
            variant="ghost"
            block
            disabled={busy}
            onClick={() => setPersonalizeOpen(false)}
          >
            Cancel
          </AppButton>
        </div>
      </Modal>
    </PageContainer>
  );
}
