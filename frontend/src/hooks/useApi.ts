import { useCallback, useEffect, useState } from "react";

export interface ApiState<T> {
  data: T | undefined;
  loading: boolean;
  error: Error | undefined;
  reload: () => void;
}

/** Runs `load` whenever `key` changes; ignores responses that arrive out of order. */
export function useApi<T>(load: () => Promise<T>, key: string): ApiState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(undefined);
    load()
      .then((result) => current && setData(result))
      .catch((err: Error) => current && setError(err))
      .finally(() => current && setLoading(false));
    return () => {
      current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, loading, error, reload };
}
