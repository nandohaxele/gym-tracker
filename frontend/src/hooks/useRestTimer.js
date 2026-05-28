// useRestTimer - frontend-only countdown timer for rest between sets (per PRD).

import { useEffect, useRef, useState } from 'react';

export default function useRestTimer(initialSeconds = 90) {
  // TODO: expose { secondsLeft, isRunning, start, pause, reset, setDuration }.
  const [duration, setDuration] = useState(initialSeconds);
  const [secondsLeft, setSecondsLeft] = useState(initialSeconds);
  const [isRunning, setIsRunning] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    // TODO: tick every 1s while running; auto-stop at 0.
    if (!isRunning) return;
    intervalRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          clearInterval(intervalRef.current);
          setIsRunning(false);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [isRunning]);

  const start = () => {
    if (secondsLeft <= 0) setSecondsLeft(duration);
    setIsRunning(true);
  };
  const pause = () => setIsRunning(false);
  const reset = () => {
    setIsRunning(false);
    setSecondsLeft(duration);
  };

  return { secondsLeft, isRunning, start, pause, reset, setDuration };
}
