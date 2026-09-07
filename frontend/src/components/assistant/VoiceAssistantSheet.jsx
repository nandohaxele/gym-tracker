import { useEffect, useMemo, useState } from 'react';
import { Loader2, Mic, MicOff, Type } from 'lucide-react';

import { executeAssistant, interpretAssistant } from '@/api/assistant.js';
import AppButton from '@/components/ui/AppButton.jsx';
import AppInput from '@/components/ui/AppInput.jsx';
import Modal from '@/components/ui/Modal.jsx';
import useSpeechRecognition from '@/hooks/useSpeechRecognition.js';
import {
  applyClarification,
  candidateLabel,
  commandPayloads,
  interpretPayload,
  isConfirmationRequired,
} from '@/lib/assistant.js';
import { SPEECH_LOCALES, preferredLocale } from '@/lib/speech.js';
import { getAssistantLocale, setAssistantLocale } from '@/utils/storage.js';

function speechMessage(code) {
  if (code === 'microphone_denied') {
    return 'Microphone blocked. Type the command instead.';
  }
  if (code === 'unavailable') {
    return 'Voice input is unavailable here. Type instead.';
  }
  if (code === 'no_speech') return 'No speech heard. Try again or type.';
  return 'Could not hear that. Type instead.';
}

export default function VoiceAssistantSheet({
  open,
  onClose,
  workoutId,
  focusWorkoutExerciseId,
  onExecuted,
}) {
  const [locale, setLocale] = useState(() =>
    preferredLocale(
      getAssistantLocale(),
      typeof navigator !== 'undefined' ? navigator.language : 'it-IT'
    )
  );
  const speech = useSpeechRecognition(locale);
  const [text, setText] = useState('');
  const [phase, setPhase] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [pendingCommands, setPendingCommands] = useState([]);

  useEffect(() => {
    if (!open) return;
    setText('');
    setPhase('idle');
    setResult(null);
    setError(null);
    setPendingCommands([]);
    speech.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, workoutId, focusWorkoutExerciseId]);

  useEffect(() => {
    if (speech.finalTranscript) {
      setText(speech.finalTranscript);
    }
  }, [speech.finalTranscript]);

  const typeOnly = !speech.supported || speech.error === 'microphone_denied';

  const changeLocale = (next) => {
    setLocale(next);
    setAssistantLocale(next);
  };

  const runInterpret = async (utterance) => {
    const trimmed = (utterance || text).trim();
    if (!trimmed) return;
    setError(null);
    setPhase('interpreting');
    try {
      const data = await interpretAssistant(
        interpretPayload({
          text: trimmed,
          workoutId,
          focusWorkoutExerciseId,
          locale,
        })
      );
      setResult(data);
      const commands = commandPayloads(data);
      setPendingCommands(commands);
      if (data.status === 'needs_clarification') {
        setPhase('clarification');
        return;
      }
      if (data.status === 'ready' && isConfirmationRequired(data)) {
        setPhase('confirmation');
        return;
      }
      if (data.status === 'ready') {
        await runExecute(commands);
        return;
      }
      setPhase('error');
    } catch (err) {
      setError(err?.message || 'Assistant request failed');
      setPhase('error');
    }
  };

  const runExecute = async (commands) => {
    setPhase('executing');
    setError(null);
    try {
      const data = await executeAssistant(commands);
      setResult((current) => ({ ...current, execute: data }));
      if (data.status === 'needs_clarification') {
        setPendingCommands(commands);
        setResult((current) => ({
          ...current,
          status: 'needs_clarification',
          reason: data.reason,
          message: data.message,
          candidates: data.candidates,
        }));
        setPhase('clarification');
        return;
      }
      if (data.status === 'error') {
        setError(data.message || 'Could not run that command');
        setPhase('error');
        onExecuted?.(data);
        return;
      }
      setPhase('success');
      onExecuted?.(data);
    } catch (err) {
      setError(err?.message || 'Could not run that command');
      setPhase('error');
    }
  };

  const chooseCandidate = (candidate) => {
    const next = applyClarification(pendingCommands, result?.reason, candidate);
    setPendingCommands(next);
    if (
      next.some((item) =>
        ['create_session', 'start_template', 'finish_session'].includes(item.type)
      )
    ) {
      setPhase('confirmation');
      return;
    }
    runExecute(next);
  };

  const displayText = speech.listening
    ? speech.interimTranscript || text
    : text;

  const title = useMemo(() => {
    if (typeOnly) return 'Assistant';
    if (speech.listening) return 'Listening…';
    return 'Voice assistant';
  }, [speech.listening, typeOnly]);

  return (
    <Modal open={open} onClose={onClose} title={title}>
      <div className="flex flex-col gap-4 px-4 py-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex gap-1">
            {SPEECH_LOCALES.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => changeLocale(item.id)}
                className={`h-9 rounded-lg px-3 text-xs font-semibold ${
                  locale === item.id
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          {typeOnly ? (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Type className="h-3.5 w-3.5" aria-hidden="true" />
              Type only
            </span>
          ) : null}
        </div>

        {speech.error ? (
          <p className="text-sm text-muted-foreground">{speechMessage(speech.error)}</p>
        ) : null}

        <AppInput
          label="Command"
          placeholder={locale.startsWith('it') ? 'es. aggiungi panca piana' : 'e.g. add bench press'}
          value={displayText}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              runInterpret(text);
            }
          }}
        />

        <div className="flex gap-2">
          {!typeOnly && (
            <AppButton
              type="button"
              variant={speech.listening ? 'destructive' : 'outline'}
              onClick={() => (speech.listening ? speech.stop() : speech.start())}
            >
              {speech.listening ? (
                <MicOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Mic className="h-4 w-4" aria-hidden="true" />
              )}
              {speech.listening ? 'Stop' : 'Speak'}
            </AppButton>
          )}
          <AppButton
            type="button"
            block
            disabled={phase === 'interpreting' || phase === 'executing' || !text.trim()}
            onClick={() => runInterpret(text)}
          >
            {phase === 'interpreting' ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : null}
            Send
          </AppButton>
        </div>

        {phase === 'confirmation' && result?.preview ? (
          <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3">
            <p className="text-sm font-medium">{result.preview}</p>
            <div className="flex gap-2">
              <AppButton type="button" variant="outline" onClick={() => setPhase('idle')}>
                Cancel
              </AppButton>
              <AppButton type="button" block onClick={() => runExecute(pendingCommands)}>
                Confirm
              </AppButton>
            </div>
          </div>
        ) : null}

        {phase === 'clarification' ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground">
              {result?.message || 'Choose one'}
            </p>
            {(result?.candidates || []).map((candidate) => (
              <AppButton
                key={candidate.id}
                type="button"
                variant="outline"
                block
                onClick={() => chooseCandidate(candidate)}
              >
                {candidateLabel(result?.reason, candidate)}
              </AppButton>
            ))}
          </div>
        ) : null}

        {phase === 'executing' ? (
          <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Updating workout…
          </p>
        ) : null}

        {phase === 'success' ? (
          <p className="text-sm font-medium text-primary">
            {result?.preview || result?.execute?.message || 'Done'}
          </p>
        ) : null}

        {phase === 'error' ? (
          <p className="text-sm text-destructive">
            {error || result?.message || 'Something went wrong'}
          </p>
        ) : null}
      </div>
    </Modal>
  );
}
