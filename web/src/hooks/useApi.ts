/**
 * Generic API hook for data fetching with loading/error states
 */

import { useCallback, useEffect, useState } from "react";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
    // biome-ignore lint/correctness/useExhaustiveDependencies: Dynamic deps by design
  }, deps);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

interface UseMutationState<T, P> {
  mutate: (params: P) => Promise<T | null>;
  data: T | null;
  loading: boolean;
  error: string | null;
  reset: () => void;
}

export function useMutation<T, P>(
  mutator: (params: P) => Promise<T>,
): UseMutationState<T, P> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(
    async (params: P): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await mutator(params);
        setData(result);
        return result;
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [mutator],
  );

  const reset = useCallback(() => {
    setData(null);
    setError(null);
  }, []);

  return { mutate, data, loading, error, reset };
}
