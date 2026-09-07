import { describe, expect, it } from 'vitest';

import {
  createRecognizer,
  extractFinalTranscript,
  extractInterimTranscript,
  getSpeechRecognitionCtor,
  isSpeechSupported,
  normalizeSpeechError,
  preferredLocale,
} from './speech.js';

describe('speech helpers', () => {
  it('treats a missing SpeechRecognition API as unsupported', () => {
    const globalObj = {};
    expect(isSpeechSupported(globalObj)).toBe(false);
    expect(getSpeechRecognitionCtor(globalObj)).toBeNull();
  });

  it('detects webkitSpeechRecognition', () => {
    const ctor = function webkitSpeechRecognition() {};
    const globalObj = { webkitSpeechRecognition: ctor };
    expect(isSpeechSupported(globalObj)).toBe(true);
    expect(getSpeechRecognitionCtor(globalObj)).toBe(ctor);
  });

  it('prefers stored locale then English, otherwise Italian', () => {
    expect(preferredLocale('en-US', 'it-IT')).toBe('en-US');
    expect(preferredLocale(null, 'en-GB')).toBe('en-US');
    expect(preferredLocale(null, 'it-IT')).toBe('it-IT');
    expect(preferredLocale(null, 'fr-FR')).toBe('it-IT');
  });

  it('extracts final and interim transcripts', () => {
    const event = {
      results: [
        { isFinal: true, 0: { transcript: 'aggiungi ' } },
        { isFinal: false, 0: { transcript: 'panca' } },
      ],
    };
    expect(extractFinalTranscript(event)).toBe('aggiungi');
    expect(extractInterimTranscript(event)).toBe('panca');
  });

  it('maps microphone denial', () => {
    expect(normalizeSpeechError('not-allowed')).toBe('microphone_denied');
  });

  it('applies language and one-shot settings on the recognizer', () => {
    function FakeRecognition() {
      this.lang = '';
      this.continuous = true;
      this.interimResults = false;
    }
    const recognition = createRecognizer({
      locale: 'en-US',
      ctor: FakeRecognition,
    });
    expect(recognition.lang).toBe('en-US');
    expect(recognition.continuous).toBe(false);
    expect(recognition.interimResults).toBe(true);
  });
});
