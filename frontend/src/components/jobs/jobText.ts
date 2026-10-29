import { he } from "../../i18n/he";
import type { JobListItem } from "../../types/api";

/** Who published the job: the agencies it was scraped from, or "posted on the site". */
export function publishedBy(job: Pick<JobListItem, "is_manual" | "recruitment_companies">): string {
  return job.is_manual ? he.manual : job.recruitment_companies.join(", ");
}
