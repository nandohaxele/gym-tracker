// Pure helpers for interpret/execute payloads and clarification.

export function interpretPayload({
  text,
  workoutId,
  focusWorkoutExerciseId,
  locale,
}) {
  const payload = { text };
  if (workoutId) payload.workout_id = Number(workoutId);
  if (focusWorkoutExerciseId) {
    payload.focus_workout_exercise_id = Number(focusWorkoutExerciseId);
  }
  if (locale) payload.locale = locale.startsWith('it') ? 'it' : 'en';
  return payload;
}

export function isConfirmationRequired(result) {
  return Boolean(result?.status === 'ready' && result.confirmation_required);
}

export function commandPayloads(result) {
  return (result?.commands || []).map((item) => item.payload || item);
}

export function applyClarification(commands, reason, candidate) {
  const next = (commands || []).map((item) => ({ ...item }));
  if (!candidate) return next;
  if (reason === 'session') {
    return next.map((item) =>
      ['add_exercise', 'record_set', 'finish_session'].includes(item.type)
        ? { ...item, workout_id: candidate.id }
        : item
    );
  }
  if (reason === 'exercise') {
    return next.map((item) =>
      item.type === 'add_exercise'
        ? { ...item, query: candidate.name }
        : item.type === 'record_set'
          ? { ...item, exercise_query: candidate.name }
          : item
    );
  }
  if (reason === 'template') {
    return next.map((item) =>
      item.type === 'start_template'
        ? { ...item, template_id: candidate.id, query: candidate.name }
        : item
    );
  }
  if (reason === 'workout_exercise') {
    return next.map((item) =>
      item.type === 'record_set'
        ? { ...item, workout_exercise_id: candidate.id }
        : item
    );
  }
  return next;
}

export function createdWorkoutId(executeResult) {
  const rows = [
    ...(executeResult?.executed || []),
    ...(executeResult?.results || []),
  ];
  for (const row of rows) {
    if (
      (row.type === 'create_session' || row.type === 'start_template') &&
      row.status === 'executed' &&
      row.data?.id
    ) {
      return row.data.id;
    }
  }
  return null;
}

export function didFinishSession(executeResult) {
  return (executeResult?.results || []).some(
    (row) => row.type === 'finish_session' && row.status === 'executed'
  );
}

export function shouldReloadSession(executeResult) {
  return (executeResult?.results || []).some(
    (row) =>
      row.status === 'executed' &&
      ['add_exercise', 'record_set', 'finish_session'].includes(row.type)
  );
}

export function candidateLabel(reason, candidate) {
  if (!candidate) return '';
  if (reason === 'session') {
    return [candidate.name, candidate.date].filter(Boolean).join(' · ');
  }
  if (reason === 'template') {
    const scope = candidate.is_global ? 'Global' : 'Personal';
    return `${candidate.name} (${scope})`;
  }
  if (reason === 'workout_exercise') {
    return candidate.exercise_name || `Exercise ${candidate.id}`;
  }
  const tracking = candidate.primary_tracking_type
    ? ` · ${candidate.primary_tracking_type}`
    : '';
  return `${candidate.name || candidate.exercise_name || candidate.id}${tracking}`;
}
