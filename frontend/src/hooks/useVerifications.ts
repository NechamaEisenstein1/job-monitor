import { useState } from "react";

import { api } from "../services/api";
import type { VerificationResult } from "../types/api";
import { useApi } from "./useApi";

export interface Verifications {
  /** Ids of jobs the user confirmed ("the details are correct"). */
  verifiedIds: Set<number>;
  /** Counts returned by the user's own votes on this page; fresher than the loaded list. */
  latest: Record<number, VerificationResult>;
  toggle: (jobId: number, verified: boolean) => Promise<void>;
  /** A failed vote, or a failed load of the user's votes. */
  error: string | undefined;
}

/** Load once per page and pass down to the buttons. */
export function useVerifications(): Verifications {
  const list = useApi(api.myVerifications, "verifications");
  const [latest, setLatest] = useState<Record<number, VerificationResult>>({});
  const [error, setError] = useState<string>();

  async function toggle(jobId: number, verified: boolean) {
    setError(undefined);
    try {
      const result = await api.verifyJob(jobId, verified);
      setLatest((prev) => ({ ...prev, [jobId]: result }));
    } catch (err) {
      setError((err as Error).message);
    }
    list.reload();
  }

  return { verifiedIds: new Set(list.data ?? []), latest, toggle, error: error ?? list.error?.message };
}
