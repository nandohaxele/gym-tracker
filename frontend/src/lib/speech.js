// Browser Web Speech API helpers. No network.

export const SPEECH_LOCALES = [
  { id: 'it-IT', label: 'IT' },
  { id: 'en-US', label: 'EN' },
];

export function getSpeechRecognitionCtor(globalObj = globalThis) {
  return globalObj.SpeechRecognition || globalObj.webkitSpeechRecognition || null;
}

export function isSpeechSupported(globalObj = globalThis) {
  return Boolean(getSpeechRecognitionCtor(globalObj));
}

export function preferredLocale(stored, navigatorLanguage) {
  if (stored === 'it-IT' || stored === 'en-US') return stored;
  const lang = String(navigatorLanguage || '').toLowerCase();
  if (lang.startsWith('en')) return 'en-US';
  return 'it-IT';
}

export function extractFinalTranscript(event) {
  const results = event?.results;
  if (!results) return '';
  let text = '';
  for (let i = 0; i < results.length; i += 1) {
    const row = results[i];
    if (row?.isFinal && row[0]?.transcript) {
      text += row[0].transcript;
    }
  }
  return text.trim();
}

export function extractInterimTranscript(event) {
  const results = event?.results;
  if (!results) return '';
  let text = '';
  for (let i = 0; i < results.length; i += 1) {
    const row = results[i];
    if (row && !row.isFinal && row[0]?.transcript) {
      text += row[0].transcript;
    }
  }
  return text.trim();
}

export function normalizeSpeechError(error) {
  if (error === 'not-allowed' || error === 'service-not-allowed') {
    return 'microphone_denied';
  }
  if (error === 'no-speech') return 'no_speech';
  if (error === 'audio-capture') return 'unavailable';
  if (error === 'network') return 'unavailable';
  return error || 'speech_error';
}

export function createRecognizer({
  locale = 'it-IT',
  onInterim,
  onFinal,
  onError,
  onEnd,
  ctor,
  globalObj = globalThis,
} = {}) {
  const Recognition = ctor || getSpeechRecognitionCtor(globalObj);
  if (!Recognition) return null;

  const recognition = new Recognition();
  recognition.lang = locale;
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  recognition.onresult = (event) => {
    const interim = extractInterimTranscript(event);
    if (interim) onInterim?.(interim);
    const finalText = extractFinalTranscript(event);
    if (finalText) onFinal?.(finalText);
  };
  recognition.onerror = (event) => {
    onError?.(normalizeSpeechError(event?.error));
  };
  recognition.onend = () => {
    onEnd?.();
  };

  return recognition;
}
