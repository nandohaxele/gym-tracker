import { Link, useNavigate } from 'react-router-dom';
import { ClipboardList, Loader2, AlertCircle, RotateCw, Plus, Play, Pencil } from 'lucide-react';

import { listTemplates, startTemplate } from '@/api/templates.js';
import useAsync from '@/hooks/useAsync.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import StatusView from '@/components/ui/StatusView.jsx';
import AppButton, { buttonVariants } from '@/components/ui/AppButton.jsx';
import { cn } from '@/lib/utils.js';
import { useState } from 'react';

function TemplateRow({ template, onStart, startingId }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border bg-card px-4 py-4 shadow-sm">
      <Link to={`/templates/${template.id}`} className="min-w-0 flex-1">
        <p className="truncate font-semibold leading-tight">{template.name}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {template.is_global ? 'Global' : 'My template'}
        </p>
      </Link>
      <div className="flex shrink-0 items-center gap-2">
        {!template.is_global && (
          <Link
            to={`/templates/${template.id}/edit`}
            aria-label={`Edit ${template.name}`}
            className={cn(buttonVariants({ variant: 'ghost', size: 'icon' }))}
          >
            <Pencil className="h-4 w-4" />
          </Link>
        )}
        <AppButton
          size="sm"
          disabled={startingId === template.id}
          onClick={() => onStart(template.id)}
        >
          <Play className="h-4 w-4" aria-hidden="true" />
          Start
        </AppButton>
      </div>
    </div>
  );
}

export default function TemplatesPage() {
  const navigate = useNavigate();
  const { data: templates, error, loading, reload } = useAsync(listTemplates, []);
  const [startingId, setStartingId] = useState(null);
  const [startError, setStartError] = useState(null);

  const globals = (templates || []).filter((item) => item.is_global);
  const mine = (templates || []).filter((item) => !item.is_global);

  const handleStart = async (templateId) => {
    setStartingId(templateId);
    setStartError(null);
    try {
      const workout = await startTemplate(templateId);
      navigate(`/workouts/${workout.id}/edit`);
    } catch (err) {
      setStartError(err?.message || 'Could not start the template.');
      setStartingId(null);
    }
  };

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-bold tracking-tight">Templates</h1>
        <Link
          to="/templates/new"
          className={cn(buttonVariants({ size: 'sm' }))}
          aria-label="New template"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          New
        </Link>
      </header>

      {startError && (
        <p className="text-sm font-medium text-destructive">{startError}</p>
      )}

      {loading ? (
        <StatusView
          icon={Loader2}
          spinIcon
          title="Loading templates…"
          description="Fetching global and personal templates."
        />
      ) : error ? (
        <StatusView
          icon={AlertCircle}
          tone="destructive"
          title="Couldn't load templates"
          description={error}
        >
          <AppButton variant="outline" onClick={reload}>
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            Try again
          </AppButton>
        </StatusView>
      ) : (
        <div className="flex flex-col gap-8">
          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Templates
            </h2>
            {globals.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No global templates yet. You can still create your own.
              </p>
            ) : (
              globals.map((template) => (
                <TemplateRow
                  key={template.id}
                  template={template}
                  onStart={handleStart}
                  startingId={startingId}
                />
              ))
            )}
          </section>

          <section className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              My Templates
            </h2>
            {mine.length === 0 ? (
              <StatusView
                icon={ClipboardList}
                title="No personal templates"
                description="Create one, personalize a global template, or save a Session."
              >
                <Link to="/templates/new" className={cn(buttonVariants())}>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  New template
                </Link>
              </StatusView>
            ) : (
              mine.map((template) => (
                <TemplateRow
                  key={template.id}
                  template={template}
                  onStart={handleStart}
                  startingId={startingId}
                />
              ))
            )}
          </section>
        </div>
      )}
    </PageContainer>
  );
}
