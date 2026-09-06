import { useEffect, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { saveWorkoutAsTemplate } from '@/api/workouts.js';
import Modal from '@/components/ui/Modal.jsx';
import AppInput from '@/components/ui/AppInput.jsx';
import AppButton from '@/components/ui/AppButton.jsx';

export default function SaveAsTemplateDialog({
  open,
  workoutName,
  workoutId,
  onClose,
  onSaved,
}) {
  const [name, setName] = useState(workoutName || '');
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setName(workoutName || '');
      setError(null);
    }
  }, [open, workoutName]);

  const handleSave = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError('Template name is required');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const template = await saveWorkoutAsTemplate(workoutId, trimmed);
      onSaved?.(template);
    } catch (err) {
      setError(err?.message || 'Could not save as a template.');
      setSaving(false);
    }
  };

  return (
    <Modal open={open} title="Save as My Template" onClose={saving ? undefined : onClose}>
      <div className="flex flex-col gap-4 p-4">
        <p className="text-sm text-muted-foreground">
          Uses recorded sets only. Duplicate names are rejected.
        </p>
        <AppInput
          label="Template name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoComplete="off"
        />
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3.5 py-3 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}
        <div className="flex flex-col gap-3">
          <AppButton block loading={saving} onClick={handleSave}>
            {saving ? 'Saving…' : 'Save template'}
          </AppButton>
          <AppButton variant="ghost" block disabled={saving} onClick={onClose}>
            Cancel
          </AppButton>
        </div>
      </div>
    </Modal>
  );
}
