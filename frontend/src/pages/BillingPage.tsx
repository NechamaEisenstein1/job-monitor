import { useState } from "react";

import { Card, PageHeader, td, th } from "../components/Layout";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { Badge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";
import { he } from "../i18n/he";
import { api } from "../services/api";
import { formatDate, formatDateTime } from "../services/format";
import type { SubscriptionState } from "../types/api";

const b = he.billing;
const STATUS_TONE = { inactive: "slate", trial: "blue", active: "green" } as const;
const primary = "rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50";
const secondary = "rounded-md px-3 py-1.5 text-sm font-medium text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-50";

function SubscriptionCard({ state, onChange }: { state: SubscriptionState; onChange: () => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string }>();

  async function run(action: () => Promise<SubscriptionState>) {
    setBusy(true);
    setMessage(undefined);
    try {
      await action();
      setMessage({ ok: true, text: b.activated });
      onChange();
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  const subscribed = state.status !== "inactive";
  return (
    <Card title={b.subscription}>
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone={STATUS_TONE[state.status]}>{b.statuses[state.status]}</Badge>
        {state.current && <span className="text-sm text-slate-600">{b.validUntil} {formatDate(state.current.expires_at)}</span>}
        <span className="text-sm text-slate-500">{b.price(state.price_ils, state.days)}</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {state.free_checkout && (
          <button disabled={busy} className={primary} onClick={() => run(() => api.checkout("free"))}>
            {subscribed ? b.renew : b.activateFree}
          </button>
        )}
        {state.price_points > 0 && (
          <button disabled={busy || state.points_balance < state.price_points}
                  className={state.free_checkout ? secondary : primary}
                  onClick={() => run(() => api.checkout("points"))}>
            {b.payWithPoints(state.price_points)}
          </button>
        )}
        {state.trial_available && !subscribed && state.trial_days > 0 && (
          <button disabled={busy} className={secondary} onClick={() => run(api.startTrial)}>
            {b.startTrial(state.trial_days)}
          </button>
        )}
      </div>
      {state.free_checkout && <p className="mt-3 text-xs text-slate-500">{b.freeNote}</p>}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={`mt-3 text-sm ${message.ok ? "text-emerald-700" : "text-rose-700"}`}>
          {message.text}
        </p>
      )}
    </Card>
  );
}

export function BillingPage() {
  const wallet = useApi(api.wallet, "wallet");
  const subscription = useApi(api.subscription, "subscription");
  const reload = () => { wallet.reload(); subscription.reload(); };

  return (
    <>
      <PageHeader title={b.title} subtitle={b.subtitle} />
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs font-medium text-slate-500">{b.balance}</p>
            <p className={`mt-1 text-3xl font-semibold tabular-nums ${(wallet.data?.balance ?? 0) < 0 ? "text-rose-700" : "text-slate-900"}`}>
              {wallet.data ? wallet.data.balance.toLocaleString("he-IL") : "…"}
            </p>
          </div>
          {subscription.error ? <ErrorState error={subscription.error} onRetry={subscription.reload} />
            : subscription.data ? <SubscriptionCard state={subscription.data} onChange={reload} />
            : <LoadingState />}
        </div>
        <div className="min-w-0 lg:col-span-2">
          <Card title={b.history} flush>
            {wallet.error ? <div className="p-4"><ErrorState error={wallet.error} onRetry={wallet.reload} /></div>
              : !wallet.data ? <LoadingState />
              : !wallet.data.transactions.length ? <EmptyState title={b.noHistory} />
              : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-slate-100">
                    <thead className="bg-slate-50">
                      <tr>{[he.admin.day, "", he.admin.points].map((h, i) => <th key={i} className={th}>{h}</th>)}</tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {wallet.data.transactions.map((t) => (
                        <tr key={t.id}>
                          <td className={`${td} whitespace-nowrap`}>{formatDateTime(t.created_at)}</td>
                          <td className={td}>{b.actions[t.action_type] ?? t.action_type}</td>
                          <td className={`${td} ltr text-end font-medium tabular-nums ${t.amount < 0 ? "text-rose-700" : "text-emerald-700"}`}>
                            {t.amount > 0 ? `+${t.amount}` : t.amount}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </Card>
        </div>
      </div>
    </>
  );
}
