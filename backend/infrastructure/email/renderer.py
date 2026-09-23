from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape

from backend.application.dto import DigestItem
from backend.domain.services.user_matching import AlertItem

_CHANGE_LABELS = {
    "new": "משרה חדשה",
    "content_updated": "עודכן תוכן",
    "new_source": "מקור נוסף",
    "source_url_updated": "קישור עודכן",
}


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str
    reply_to: str | None = None


def render_digest(items: list[DigestItem], scheduled_date: date, subject_template: str) -> RenderedEmail:
    subject = subject_template.format(date=scheduled_date.isoformat())
    rows, lines = [], [subject, ""]
    for item in items:
        labels = ", ".join(_CHANGE_LABELS.get(c, c) for c in item.changes)
        meta = " · ".join(filter(None, [item.client_company, item.location, f"score {item.junior_score:.2f}"]))
        links = " ".join(f'<a href="{escape(u)}">מקור {i + 1}</a>' for i, u in enumerate(item.source_urls))
        rows.append(
            f"<tr><td style='padding:8px;border-bottom:1px solid #e5e7eb'>"
            f"<strong>{escape(item.title)}</strong><br>"
            f"<span style='color:#6b7280'>{escape(meta)}</span><br>"
            f"<span style='color:#2563eb'>{escape(labels)}</span> {links}</td></tr>"
        )
        lines.append(f"- {item.title} ({meta}) [{labels}]")
        lines.extend(f"  {u}" for u in item.source_urls)
    html = (
        f"<html><body dir='rtl' style='font-family:Arial,sans-serif'>"
        f"<h2>{escape(subject)}</h2><p>{len(items)} משרות</p>"
        f"<table style='border-collapse:collapse;width:100%'>{''.join(rows)}</table></body></html>"
    )
    return RenderedEmail(subject=subject, html=html, text="\n".join(lines))


_TENDER = "מכרז ממשלתי"


def _page(title: str, body: str) -> str:
    return (f"<html><body dir='rtl' style='font-family:Arial,sans-serif;color:#0f172a'>"
            f"<h2 style='margin:0 0 12px'>{escape(title)}</h2>{body}</body></html>")


def render_user_alert(display_name: str, items: list[AlertItem], scheduled_date: date,
                      subject_template: str, base_url: str) -> RenderedEmail:
    """Government tenders first, then jobs where the user already knows a recruiter."""
    subject = subject_template.format(date=scheduled_date.isoformat())
    rows, lines = [], [f"שלום {display_name},", "", subject, ""]
    for item in sorted(items, key=lambda i: i.priority, reverse=True):
        badges = []
        if item.is_government_tender:
            badges.append(f"<span style='background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:4px'>{_TENDER}</span>")
        if item.recruiter_names:
            badges.append(f"<span style='color:#047857'>מכירים שם: {escape(', '.join(item.recruiter_names))}</span>")
        meta = " · ".join(filter(None, [item.client_company, item.location]))
        link = f"{base_url.rstrip('/')}/jobs/{item.job_id}"
        rows.append(
            f"<tr><td style='padding:10px;border-bottom:1px solid #e5e7eb'>"
            f"<a href='{escape(link)}' style='font-weight:bold;color:#0369a1'>{escape(item.title)}</a> "
            f"{' '.join(badges)}<br><span style='color:#64748b'>{escape(meta)}</span></td></tr>")
        tags = (f" [{_TENDER}]" if item.is_government_tender else "") + (
            f" [מכירים: {', '.join(item.recruiter_names)}]" if item.recruiter_names else "")
        lines += [f"- {item.title}{tags} ({meta})", f"  {link}"]
    body = (f"<p>שלום {escape(display_name)}, נמצאו {len(items)} משרות חדשות שמתאימות לפרופיל שלך:</p>"
            f"<table style='border-collapse:collapse;width:100%'>{''.join(rows)}</table>"
            f"<p style='color:#64748b;font-size:12px'>ניתן לכבות התראות באזור האישי.</p>")
    return RenderedEmail(subject=subject, html=_page(subject, body), text="\n".join(lines))


def render_outreach(*, recruiter_name: str, sender_name: str, sender_email: str, job_title: str,
                    job_company: str | None, job_url: str, is_government_tender: bool) -> RenderedEmail:
    """One personal email to one recruiter. Replies go straight to the user (Reply-To)."""
    kind = "למכרז" if is_government_tender else "למשרה"
    where = f" ב{job_company}" if job_company else ""
    subject = f"בקשת סיוע בהגשת מועמדות: {job_title}"
    paragraphs = [
        f"שלום {recruiter_name},",
        f"אני {sender_name}, ואשמח לעזרתך בהגשת מועמדות {kind} \"{job_title}\"{where}.\nקישור למשרה: {job_url}",
        "אם תוכל/י להמליץ עליי, להעביר את קורות החיים שלי או לכוון אותי לאיש הקשר הנכון - אודה מאוד.",
        f"תודה רבה,\n{sender_name}\n{sender_email}",
    ]
    text = "\n\n".join(paragraphs)
    html = _page(subject, "".join(f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs))
    return RenderedEmail(subject=subject, html=html, text=text, reply_to=sender_email)


def render_verification(display_name: str, link: str) -> RenderedEmail:
    subject = "אימות כתובת המייל - מוניטור משרות"
    paragraphs = [
        f"שלום {display_name},",
        "כדי לקבל התראות על משרות ולשלוח פניות למגייסים, יש לאמת את כתובת המייל:",
        link,
        "הקישור בתוקף ל-48 שעות. אם לא נרשמת - אפשר להתעלם מהמייל.",
    ]
    button = (f"<p><a href='{escape(link)}' style='background:#0f172a;color:#fff;padding:10px 16px;"
              f"border-radius:6px;text-decoration:none'>אימות כתובת המייל</a></p>")
    html = _page(subject, f"<p>{escape(paragraphs[0])}</p><p>{escape(paragraphs[1])}</p>{button}"
                          f"<p style='color:#64748b;font-size:12px'>{escape(paragraphs[3])}</p>")
    return RenderedEmail(subject=subject, html=html, text=chr(10).join(paragraphs))
