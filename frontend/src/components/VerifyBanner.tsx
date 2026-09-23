import { useState } from "react";

import { useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";

/** Shown until the user confirms their email - alerts and outreach wait for it. */
export function VerifyBanner() {
  const user = useUser();
  const [status, setStatus] = useState<string>();
  if (user.email_verified) return null;

  async function resend() {
    try {
      await api.resendVerification();
      setStatus(he.auth.resent);
    } catch (err) {
      setStatus((err as Error).message);
    }
  }

  return (
    <div role="status" className="border-b border-amber-200 bg-amber-50">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-2 text-sm text-amber-900 sm:px-6">
        <span>✉ {he.auth.verifyBanner(user.email)}</span>
        <button onClick={resend} className="rounded-md bg-white px-2 py-0.5 text-xs font-medium ring-1 ring-amber-300 hover:bg-amber-100">
          {he.auth.resend}
        </button>
        {status && <span className="text-xs">{status}</span>}
      </div>
    </div>
  );
}
