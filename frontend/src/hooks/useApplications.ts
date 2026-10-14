import { useState } from "react";

import { api } from "../services/api";
import type { JobApplication } from "../types/api";
import { type ApiState, useApi } from "./useApi";

export interface Applications {
  list: ApiState<JobApplication[]>;
  /** Ids of jobs (still on the board) the user marked "I applied". */
  appliedIds: Set<number>;
  toggle: (jobId: number, applied: boolean) => Promise<void>;
  /** A failed update, or a failed load of the list. */
  error: string | undefined;
}

/** Load once per page and pass down to the checkboxes. */
export function useApplications(): Applications {
  const list = useApi(api.applications, "applications");
  const [error, setError] = useState<string>();
  const appliedIds = new Set((list.data ?? []).flatMap((a) => (a.job_id === null ? [] : [a.job_id])));

  async function toggle(jobId: number, applied: boolean) {
    setError(undefined);
    try {
      await (applied ? api.markApplied(jobId) : api.unmarkApplied(jobId));
    } catch (err) {
      setError((err as Error).message);
    }
    list.reload();
  }

  // A failed load must not look like "nothing applied": report it like a failed update.
  return { list, appliedIds, toggle, error: error ?? list.error?.message };
}
