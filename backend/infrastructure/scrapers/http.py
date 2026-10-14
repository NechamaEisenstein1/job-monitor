"""The single shared retry implementation used by every HTTP-based scraper."""
from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from backend.infrastructure.scrapers.base import HttpStatusError, NetworkError, ScrapeTimeoutError
from backend.observability import log_event

RETRYABLE_STATUS = frozenset({429, 502, 503, 504})
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


# Headers that tell which protection layer answered a refused request. Cookies are never logged.
_DIAGNOSTIC_HEADERS = ("server", "via", "x-cdn", "cf-ray", "cf-mitigated", "x-iinfo", "x-sucuri-id",
                       "x-akamai-transformed", "akamai-grn", "x-amz-cf-id", "x-cache", "x-powered-by")
# (header, value substring or None for "header present", name of the protection)
_BLOCKERS = (
    ("cf-mitigated", None, "Cloudflare challenge"),
    ("cf-ray", None, "Cloudflare"),
    ("x-iinfo", None, "Imperva/Incapsula"),
    ("x-cdn", "imperva", "Imperva/Incapsula"),
    ("x-sucuri-id", None, "Sucuri"),
    ("akamai-grn", None, "Akamai"),
    ("server", "akamaighost", "Akamai"),
    ("x-amz-cf-id", None, "AWS CloudFront/WAF"),
    ("server", "cloudflare", "Cloudflare"),
)


def _diagnostic_headers(headers: httpx.Headers) -> dict[str, str]:
    return {k: headers[k][:120] for k in _DIAGNOSTIC_HEADERS if k in headers}


def describe_block(response: httpx.Response) -> str:
    """Best guess at what refused the request, from headers plus the page title."""
    headers = response.headers
    blocker = next((name for header, needle, name in _BLOCKERS
                    if header in headers and (needle is None or needle in headers[header].lower())), None)
    parts = [blocker or f"server={headers.get('server', 'unknown')[:40]}"]
    match = _TITLE.search(response.text[:5000]) if response.content else None
    if match and match.group(1).strip():
        parts.append(f"page title: {' '.join(match.group(1).split())[:80]}")
    return "; ".join(parts)


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int
    backoff_base_seconds: float
    max_backoff_seconds: float = 60.0

    def backoff(self, attempt: int) -> float:
        return min(self.max_backoff_seconds, self.backoff_base_seconds * (2 ** attempt))


def parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (when - now).total_seconds())


class RetryingHttpClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        policy: RetryPolicy,
        rate_limit_per_site: float | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self._client = client
        self._policy = policy
        self._min_interval = 1.0 / rate_limit_per_site if rate_limit_per_site else 0.0
        self._sleep = sleep
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _throttle(self, url: str) -> None:
        if not self._min_interval:
            return
        host = urlsplit(url).netloc
        async with self._locks.setdefault(host, asyncio.Lock()):
            wait = self._last_request.get(host, 0.0) + self._min_interval - time.monotonic()
            if wait > 0:
                await self._sleep(wait)
            self._last_request[host] = time.monotonic()

    async def get(self, url: str, **kwargs: object) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: object) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        attempt = 0
        while True:
            await self._throttle(url)
            try:
                response = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                if attempt >= self._policy.max_retries:
                    raise ScrapeTimeoutError(f"timeout after {attempt + 1} attempts: {url}") from exc
                delay, reason = self._policy.backoff(attempt), "timeout"
            except httpx.TransportError as exc:
                if attempt >= self._policy.max_retries:
                    raise NetworkError(f"{type(exc).__name__} after {attempt + 1} attempts: {url}") from exc
                delay, reason = self._policy.backoff(attempt), type(exc).__name__
            else:
                if response.status_code in RETRYABLE_STATUS:
                    if attempt >= self._policy.max_retries:
                        raise HttpStatusError(response.status_code, url)
                    delay = self._policy.backoff(attempt)
                    if response.status_code == 429:
                        retry_after = parse_retry_after(response.headers.get("Retry-After"))
                        if retry_after is not None:
                            delay = min(retry_after, self._policy.max_backoff_seconds)
                    reason = f"http_{response.status_code}"
                elif response.is_error:
                    detail = None
                    if response.status_code in (401, 403):
                        detail = describe_block(response)
                        log_event("http_blocked", url=url, status=response.status_code, blocker=detail,
                                  headers=_diagnostic_headers(response.headers))
                    raise HttpStatusError(response.status_code, url, detail)  # 404 etc: not retried
                else:
                    return response
            attempt += 1
            log_event("http_retry", url=url, attempt=attempt, reason=reason, delay_seconds=round(delay, 2))
            await self._sleep(delay)
