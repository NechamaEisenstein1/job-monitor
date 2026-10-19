"""Shared normalization. No matching, no scoring here."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from backend.domain.models import NormalizedJob, RawJob

# Query parameters that never identify a job posting.
TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "ref", "referrer", "trk",
})
_LEGAL_SUFFIXES = frozenset({"ltd", "inc", "llc", "בעמ", "בע", "מ"})
_INLINE_WS = re.compile(r"[ \t ‏‎]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_NON_WORD = re.compile(r"[^\w]+", re.UNICODE)
# Longest stored value per short field (the jobs / job_sources column sizes). Some boards
# list every region a job may be in, which runs past the location column.
_MAX_LEN = {"title": 500, "client_company": 300, "employment_type": 100,
            "location": 200, "region": 200, "source_job_id": 200}


def clean_text(value: str | None) -> str | None:
    """Single-line cleanup; empty -> None."""
    if value is None:
        return None
    value = unicodedata.normalize("NFKC", str(value))
    value = " ".join(value.split())
    return value or None


def clean_multiline(value: str | None) -> str:
    """Keeps paragraph breaks; collapses everything else."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", str(value)).replace("\r\n", "\n").replace("\r", "\n")
    lines = [_INLINE_WS.sub(" ", line).strip() for line in value.split("\n")]
    return _MULTI_NEWLINE.sub("\n\n", "\n".join(lines)).strip()


def clip(value: str | None, limit: int) -> str | None:
    """Shortens an over-long single-line value at a word boundary, marking the cut with '…'."""
    if value is None or len(value) <= limit:
        return value
    cut = value[:limit - 1]
    if " " in cut:
        cut = cut[:cut.rindex(" ")]
    return cut.rstrip(" ,;-") + "…"


def comparison_key(value: str | None) -> str:
    """Lowercase, punctuation-free form for equality/similarity comparisons."""
    if not value:
        return ""
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(_NON_WORD.sub(" ", value).split())


def company_key(value: str | None) -> str:
    tokens = [t for t in comparison_key(value).split() if t not in _LEGAL_SUFFIXES]
    return " ".join(tokens)


def normalize_url(url: str | None) -> str:
    """Deterministic URL form: lowercase scheme/host, https, no tracking params,
    sorted query, no fragment, no trailing slash. Meaningful path/query is kept."""
    url = (url or "").strip()
    if not url:
        return ""
    parts = urlsplit(url)
    scheme = (parts.scheme or "https").lower()
    if scheme == "http":
        scheme = "https"
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = parts.port
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", parts.path or "")
    if path.endswith("/"):
        path = path.rstrip("/")
    query = sorted(
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    )
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))


def clean_url(url: str | None) -> str:
    """The link we store and show: the original URL minus tracking params and fragment.
    Unlike normalize_url it keeps host/scheme/slashes as the site published them."""
    url = (url or "").strip()
    if not url:
        return ""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc, parts.path, urlencode(query), ""))


def url_fingerprint(url: str | None) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def normalize_raw_job(raw: RawJob) -> NormalizedJob:
    return NormalizedJob(
        recruitment_company=clean_text(raw.recruitment_company) or "",
        source_job_id=clip(clean_text(raw.source_job_id), _MAX_LEN["source_job_id"]),
        source_url=clean_url(raw.source_url),
        title=clip(clean_text(raw.title), _MAX_LEN["title"]) or "",
        description=clean_multiline(raw.description),
        requirements=clean_multiline(raw.requirements),
        client_company=clip(clean_text(raw.client_company), _MAX_LEN["client_company"]),
        employment_type=clip(clean_text(raw.employment_type), _MAX_LEN["employment_type"]),
        location=clip(clean_text(raw.location), _MAX_LEN["location"]),
        region=clip(clean_text(raw.region), _MAX_LEN["region"]),
        published_at=raw.published_at,
        metadata=dict(raw.metadata or {}),
    )
