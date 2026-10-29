import { useState } from "react";

import type { PreviewNavigation } from "../components/jobs/JobPreview";
import { he } from "../i18n/he";
import type { JobListItem } from "../types/api";

/** Which job of the current page is open, and previous/next through the page. On wide screens
 *  the first job is shown until another is picked; on phones nothing opens until a tap. */
export function useJobSelection(jobs: JobListItem[], { offset, total, openFirst }: {
  offset: number; total: number; openFirst: boolean;
}) {
  const [pickedId, setPickedId] = useState<number>();
  const picked = jobs.findIndex((j) => j.id === pickedId);
  const index = picked >= 0 ? picked : openFirst && jobs.length ? 0 : -1;
  const job = index >= 0 ? jobs[index] : undefined;
  const goTo = (i: number) => setPickedId(jobs[i].id);

  const navigation: PreviewNavigation = {
    position: he.jobs.position(offset + index + 1, total),
    onPrevious: index > 0 ? () => goTo(index - 1) : undefined,
    onNext: index >= 0 && index < jobs.length - 1 ? () => goTo(index + 1) : undefined,
  };

  return { job, navigation, select: setPickedId, close: () => setPickedId(undefined) };
}
