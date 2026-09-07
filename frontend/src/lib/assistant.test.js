import { describe, expect, it } from 'vitest';

import {
  applyClarification,
  commandPayloads,
  createdWorkoutId,
  interpretPayload,
  isConfirmationRequired,
  shouldReloadSession,
} from './assistant.js';

describe('assistant helpers', () => {
  it('includes current workout_id in the interpret payload', () => {
    expect(
      interpretPayload({
        text: 'aggiungi panca piana',
        workoutId: '10',
        focusWorkoutExerciseId: 33,
        locale: 'it-IT',
      })
    ).toEqual({
      text: 'aggiungi panca piana',
      workout_id: 10,
      focus_workout_exercise_id: 33,
      locale: 'it',
    });
  });

  it('detects confirmation-required interpret results', () => {
    expect(
      isConfirmationRequired({
        status: 'ready',
        confirmation_required: true,
      })
    ).toBe(true);
    expect(
      isConfirmationRequired({
        status: 'ready',
        confirmation_required: false,
      })
    ).toBe(false);
  });

  it('maps clarification choices onto trusted command fields', () => {
    const commands = [
      { type: 'add_exercise', query: 'Press', workout_id: 10 },
    ];
    expect(
      applyClarification(commands, 'exercise', { id: 1, name: 'Bench Press' })
    ).toEqual([{ type: 'add_exercise', query: 'Bench Press', workout_id: 10 }]);

    expect(
      applyClarification(
        [{ type: 'finish_session' }],
        'session',
        { id: 7, name: 'Push' }
      )
    ).toEqual([{ type: 'finish_session', workout_id: 7 }]);
  });

  it('does not ask the editor to reload after an assistant error', () => {
    expect(
      shouldReloadSession({
        results: [{ type: 'add_exercise', status: 'error', message: 'nope' }],
      })
    ).toBe(false);
  });

  it('asks the editor to reload after a successful write', () => {
    const result = {
      results: [
        { type: 'add_exercise', status: 'executed', data: { id: 33 } },
      ],
    };
    expect(shouldReloadSession(result)).toBe(true);
    expect(
      createdWorkoutId({
        results: [{ type: 'start_template', status: 'executed', data: { id: 12 } }],
      })
    ).toBe(12);
  });

  it('leaves command payloads intact when extracting from interpret', () => {
    const payloads = commandPayloads({
      commands: [{ payload: { type: 'add_exercise', query: 'Bench Press' } }],
    });
    expect(payloads[0].query).toBe('Bench Press');
  });
});
