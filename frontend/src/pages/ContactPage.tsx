import { useState } from "react";

import { Card } from "../components/ui/Card";
import { PageHeader } from "../components/ui/PageHeader";
import { useUser } from "../hooks/useAuth";
import { he } from "../i18n/he";
import { api } from "../services/api";
import type { ContactCategory } from "../types/api";

const c = he.contact;
const control =
  "w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-sm focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500";
const primary = "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
const field = "flex flex-col gap-1 text-xs font-medium text-slate-500";

/** A message from the logged-in user to the site admin; admins read them in the admin area. */
export function ContactPage() {
  const user = useUser();
  const [category, setCategory] = useState<ContactCategory>("question");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState<{ error?: string; ok?: string }>({});

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    try {
      await api.contactAdmin({ category, subject, body });
      setSubject("");
      setBody("");
      setStatus({ ok: c.sent });
    } catch (err) {
      setStatus({ error: (err as Error).message });
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <PageHeader title={c.title} subtitle={c.subtitle} />
      <div className="max-w-2xl">
        <Card>
          <form onSubmit={send} className="space-y-3">
            <label className={field}>
              {c.category}
              <select className={control} value={category} onChange={(e) => setCategory(e.target.value as ContactCategory)}>
                {Object.entries(c.categories).map(([code, label]) => <option key={code} value={code}>{label}</option>)}
              </select>
            </label>
            <label className={field}>
              {c.subject}
              <input className={control} value={subject} maxLength={200} required dir="auto"
                     onChange={(e) => setSubject(e.target.value)} />
            </label>
            <label className={field}>
              {c.body}
              <textarea className={`${control} min-h-40`} value={body} maxLength={5000} required dir="auto"
                        onChange={(e) => setBody(e.target.value)} />
              <span className="font-normal text-slate-400">{c.bodyHint}</span>
            </label>
            <p className="text-xs text-slate-500">{c.replyTo(user.email)}</p>
            <div className="flex items-center gap-3">
              <button className={primary} disabled={sending}>{c.send}</button>
              {status.error && <p role="alert" className="text-sm text-rose-700">{status.error}</p>}
              {status.ok && <p role="status" className="text-sm text-emerald-700">{status.ok}</p>}
            </div>
          </form>
        </Card>
      </div>
    </>
  );
}
