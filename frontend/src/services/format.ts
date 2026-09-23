// Presentation-only formatting. No business rules here.
import { he } from "../i18n/he";

const dateTime = new Intl.DateTimeFormat("he-IL", {
  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
});
const dateOnly = new Intl.DateTimeFormat("he-IL", { day: "numeric", month: "short", year: "numeric" });

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTime.format(new Date(iso)) : he.common.none;
}

export function formatDate(iso: string | null | undefined): string {
  return iso ? dateOnly.format(new Date(iso)) : he.common.none;
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return he.common.none;
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return he.relative.justNow;
  if (minutes < 60) return he.relative.minutes(minutes);
  const hours = Math.round(minutes / 60);
  if (hours < 48) return he.relative.hours(hours);
  return he.relative.days(Math.round(hours / 24));
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return he.common.none;
  if (seconds < 60) return `${seconds.toFixed(1)} שנ׳`;
  return `${Math.floor(seconds / 60)} דק׳ ${Math.round(seconds % 60)} שנ׳`;
}

export function formatPercent(ratio: number | null | undefined): string {
  return ratio == null ? he.common.none : `${Math.round(ratio * 100)}%`;
}
