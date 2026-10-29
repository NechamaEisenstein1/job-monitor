import type { Applications } from "../../hooks/useApplications";
import { he } from "../../i18n/he";
import type { JobListItem } from "../../types/api";
import { JobListCard } from "./JobListCard";

export function JobList({ jobs, selectedId, onSelect, applications }: {
  jobs: JobListItem[];
  selectedId: number | undefined;
  onSelect: (id: number) => void;
  applications: Applications;
}) {
  return (
    <ul aria-label={he.jobs.listLabel} className="flex flex-col gap-2.5">
      {jobs.map((job) => (
        <JobListCard key={job.id} job={job} selected={job.id === selectedId} onSelect={() => onSelect(job.id)}
                     applications={applications} />
      ))}
    </ul>
  );
}
