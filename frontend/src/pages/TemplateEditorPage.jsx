import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2, AlertCircle, RotateCw } from 'lucide-react';

import { createTemplate, getTemplate, updateTemplate } from '@/api/templates.js';
import useAsync from '@/hooks/useAsync.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton from '@/components/ui/AppButton.jsx';
import TemplateForm from '@/components/templates/TemplateForm.jsx';

function mapTemplate(template) {
  return {
    name: template.name,
    exercises: [...(template.exercises || [])]
      .sort((a, b) => a.order_index - b.order_index)
      .map((ex) => ({
        exercise_id: ex.exercise.id,
        name: ex.exercise.name,
        muscle_group: ex.exercise.muscle_group,
        primary_tracking_type: ex.exercise.primary_tracking_type,
        secondary_tracking_types: ex.exercise.secondary_tracking_types || [],
        target_sets: ex.target_sets,
        target_reps_min: ex.target_reps_min ?? '',
        target_reps_max: ex.target_reps_max ?? '',
        target_duration_seconds_min: ex.target_duration_seconds_min ?? '',
        target_duration_seconds_max: ex.target_duration_seconds_max ?? '',
        target_distance_meters_min: ex.target_distance_meters_min ?? '',
        target_distance_meters_max: ex.target_distance_meters_max ?? '',
      })),
  };
}

export default function TemplateEditorPage() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const { data: template, error, loading, reload } = useAsync(
    () => (isEdit ? getTemplate(id) : Promise.resolve(null)),
    [id]
  );

  const handleSubmit = async (payload) => {
    if (isEdit) {
      const updated = await updateTemplate(id, payload);
      navigate(`/templates/${updated.id}`, { replace: true });
    } else {
      const created = await createTemplate(payload);
      navigate(`/templates/${created.id}`, { replace: true });
    }
  };

  const handleCancel = () => {
    if (isEdit) navigate(`/templates/${id}`);
    else navigate('/templates');
  };

  const defaultValues = isEdit
    ? template && mapTemplate(template)
    : { name: '', exercises: [] };

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
          {isEdit ? 'Edit template' : 'New template'}
        </h1>
      </header>

      {isEdit && loading ? (
        <StatusView icon={Loader2} spinIcon title="Loading template…" />
      ) : isEdit && error ? (
        <StatusView
          icon={AlertCircle}
          tone="destructive"
          title="Couldn't load template"
          description={error}
        >
          <AppButton variant="outline" onClick={reload}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </AppButton>
        </StatusView>
      ) : isEdit && template?.is_global ? (
        <StatusView
          title="Global templates are read-only"
          description="Personalize this template to create an editable copy."
        >
          <AppButton onClick={() => navigate(`/templates/${id}`)}>Back</AppButton>
        </StatusView>
      ) : defaultValues ? (
        <TemplateForm
          defaultValues={defaultValues}
          onSubmit={handleSubmit}
          onCancel={handleCancel}
          submitLabel={isEdit ? 'Save changes' : 'Create template'}
        />
      ) : null}
    </PageContainer>
  );
}
