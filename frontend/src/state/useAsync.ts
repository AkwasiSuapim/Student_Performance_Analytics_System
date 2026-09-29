import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";

interface AsyncState<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
}

/** Run an API call whenever `deps` change; ignores results from superseded calls. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const latest = useRef(0);

  useEffect(() => {
    const call = ++latest.current;
    setLoading(true);
    fn()
      .then((result) => {
        if (call !== latest.current) return;
        setData(result);
        setError(null);
      })
      .catch((caught) => {
        if (call !== latest.current) return;
        setError(caught instanceof ApiError ? caught : new ApiError("unknown_error", "Something went wrong."));
      })
      .finally(() => {
        if (call === latest.current) setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
