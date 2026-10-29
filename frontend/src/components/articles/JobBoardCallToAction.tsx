import { Link } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";
import { he } from "../../i18n/he";

const t = he.site.articles;

/** Closes every article: from reading about job hunting to the job board itself. */
export function JobBoardCallToAction() {
  const { user } = useAuth();

  return (
    <aside className="mt-12 rounded-xl border border-tender-200 bg-tender-50 p-6">
      <h2 className="text-lg font-semibold text-amber-950">{t.ctaTitle}</h2>
      <p className="mt-2 leading-7 text-amber-900">{t.ctaBody}</p>
      <Link to={user ? "/jobs" : "/login?mode=register"}
            className="mt-4 inline-block rounded-md bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700">
        {user ? t.ctaLoggedIn : t.cta}
      </Link>
    </aside>
  );
}
