import { useCallback, useEffect, useRef, useState } from 'react';

import {
  createRecognizer,
  isSpeechSupported,
} from '@/lib/speech.js';

export default function useSpeechRecognition(locale) {
  const [supported] = useState(() => isSpeechSupported());
  const [listening, setListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [error, setError] = useState(null);
  const recognitionRef = useRef(null);

  const stop = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      /* already stopped */
    }
    recognitionRef.current = null;
    setListening(false);
  }, []);

  const reset = useCallback(() => {
    stop();
    setInterimTranscript('');
    setFinalTranscript('');
    setError(null);
  }, [stop]);

  const start = useCallback(() => {
    if (!supported) {
      setError('unavailable');
      return;
    }
    stop();
    setError(null);
    setInterimTranscript('');
    setFinalTranscript('');
    const recognition = createRecognizer({
      locale,
      onInterim: setInterimTranscript,
      onFinal: (text) => {
        setFinalTranscript(text);
        setInterimTranscript('');
      },
      onError: (code) => {
        setError(code);
        setListening(false);
      },
      onEnd: () => {
        setListening(false);
      },
    });
    if (!recognition) {
      setError('unavailable');
      return;
    }
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch {
      setError('unavailable');
      setListening(false);
    }
  }, [locale, stop, supported]);

  useEffect(() => () => stop(), [stop]);

  return {
    supported,
    listening,
    interimTranscript,
    finalTranscript,
    error,
    start,
    stop,
    reset,
  };
}
