import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, AlertCircle } from 'lucide-react';

import { createWorkout } from '@/api/workouts.js';
import { sessionMetaSchema } from '@/lib/validators.js';
import { toDateInputValue } from '@/utils/format.js';
import PageContainer from '@/components/ui/PageContainer.jsx';
import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';

export default function StartWorkoutPage() {
  const navigate = useNavigate();
  const [serverError, setServerError] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(sessionMetaSchema),
    defaultValues: { name: 'Workout', date: toDateInputValue() },
  });

  const submit = async (values) => {
    setServerError(null);
    try {
      const created = await createWorkout({
        name: values.name.trim(),
        date: values.date,
      });
      navigate(`/workouts/${created.id}/edit`, { replace: true });
    } catch (err) {
      setServerError(err?.message || 'Could not start the workout.');
    }
  };

  return (
    <PageContainer className="flex flex-col gap-6">
      <header className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => navigate('/home')}
          aria-label="Back"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
        <h1 className="text-2xl font-bold tracking-tight">New workout</h1>
      </header>

      <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-6">
        {serverError && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{serverError}</span>
          </div>
        )}

        <AppInput
          label="Workout name"
          autoComplete="off"
          error={errors.name?.message}
          {...register('name')}
        />
        <AppInput
          label="Date"
          type="date"
          error={errors.date?.message}
          {...register('date')}
        />

        <AppButton type="submit" block size="lg" loading={isSubmitting}>
          {isSubmitting ? 'Starting…' : 'Start workout'}
        </AppButton>
        <AppButton type="button" variant="ghost" block onClick={() => navigate('/home')}>
          Cancel
        </AppButton>
      </form>
    </PageContainer>
  );
}
