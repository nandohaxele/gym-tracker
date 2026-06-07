// useAsync - tiny data-fetching helper for "load on mount" screens.
// Centralizes the loading / error / data state machine so pages don't have to
// re-implement it. Returns { data, error, loading, reload, setData }.
//
// Usage:
//   const { data, error, loading, reload } = useAsync(() => getWorkout(id), [id]);

import { useCallback, useEffect, useRef, useState } from 'react';

export default function useAsync(asyncFn, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  // Keep the latest fn without forcing consumers to memoize it themselves.
  const fnRef = useRef(asyncFn);
  fnRef.current = asyncFn;

  const run = useCallback(() => {
    let active = true;
    setLoading(true);
    setError(null);

    fnRef.current()
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (active) setError(err?.message || 'Something went wrong.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { data, error, loading, reload: run, setData };
}
