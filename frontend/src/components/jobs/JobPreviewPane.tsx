import type { Applications } from "../../hooks/useApplications";
import { useMediaQuery, WIDE_SCREEN } from "../../hooks/useMediaQuery";
import type { Verifications } from "../../hooks/useVerifications";
import { he } from "../../i18n/he";
import type { JobListItem } from "../../types/api";
import { Dialog } from "../ui/Dialog";
import { JobPreview, type PreviewNavigation } from "./JobPreview";

/** Where the selected job opens: a panel beside the list on wide screens, the whole screen on
 *  phones (closing returns to the list where it was). */
export function JobPreviewPane({ job, navigation, onClose, applications, verifications }: {
  job: JobListItem | undefined;
  navigation: PreviewNavigation;
  onClose: () => void;
  applications: Applications;
  verifications: Verifications;
}) {
  const wide = useMediaQuery(WIDE_SCREEN);
  const preview = job && (
    <JobPreview key={job.id} job={job} navigation={navigation} applications={applications} verifications={verifications} />
  );

  if (!wide) {
    return (
      <Dialog open={!!job} onClose={onClose} title={job?.title ?? he.jobs.preview} placement="fullscreen" hideHeader>
        {preview}
      </Dialog>
    );
  }
  return (
    <aside aria-label={he.jobs.preview}
           className="sticky top-20 flex max-h-[calc(100dvh-6rem)] w-[30rem] shrink-0 flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white">
      {preview ?? <p className="p-8 text-center text-slate-500">{he.jobs.pickOne}</p>}
    </aside>
  );
}
