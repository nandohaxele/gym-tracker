// RestTimer - small visual countdown using useRestTimer.

import useRestTimer from '../../hooks/useRestTimer.js';

export default function RestTimer({ seconds = 90 }) {
  const { secondsLeft, isRunning, start, pause, reset } = useRestTimer(seconds);

  // TODO: render mm:ss + start/pause/reset buttons; vibrate/beep at 0?
  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, '0');
  const ss = String(secondsLeft % 60).padStart(2, '0');

  return (
    <div className="rest-timer" role="timer" aria-live="polite">
      <div className="rest-timer__display">{mm}:{ss}</div>
      <div className="rest-timer__controls">
        {!isRunning ? (
          <button type="button" className="btn" onClick={start}>Start</button>
        ) : (
          <button type="button" className="btn" onClick={pause}>Pause</button>
        )}
        <button type="button" className="btn btn--ghost" onClick={reset}>Reset</button>
      </div>
    </div>
  );
}
