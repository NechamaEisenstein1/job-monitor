import asyncio

import httpx
import pytest

from backend.domain.enums import ScrapeStatus
from backend.infrastructure.scrapers.base import HttpStatusError, ParseError, ScrapeTimeoutError
from backend.infrastructure.scrapers.generic import JsonApiScraper
from backend.infrastructure.scrapers.http import RetryingHttpClient, RetryPolicy

URL = "https://jobs.example.com/api"


def client_for(responses, max_retries=3):
    """responses: list of httpx.Response or Exception, consumed in order."""
    calls, sleeps = [], []

    def handler(request):
        calls.append(request)
        item = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    http = RetryingHttpClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)),
                              RetryPolicy(max_retries=max_retries, backoff_base_seconds=1.0), sleep=fake_sleep)
    return http, calls, sleeps


def run(coro):
    return asyncio.run(coro)


def test_timeout_is_retried_then_succeeds():
    http, calls, sleeps = client_for([httpx.ReadTimeout("slow"), httpx.Response(200, json=[])])
    assert run(http.get(URL)).status_code == 200
    assert len(calls) == 2 and sleeps == [1.0]


def test_timeout_exhausts_retries():
    http, calls, _ = client_for([httpx.ReadTimeout("slow")], max_retries=2)
    with pytest.raises(ScrapeTimeoutError) as exc:
        run(http.get(URL))
    assert len(calls) == 3 and exc.value.status == ScrapeStatus.TIMEOUT


def test_429_without_retry_after_uses_exponential_backoff():
    http, calls, sleeps = client_for([httpx.Response(429), httpx.Response(429), httpx.Response(200)])
    run(http.get(URL))
    assert sleeps == [1.0, 2.0]


def test_429_honours_retry_after():
    http, _, sleeps = client_for([httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200)])
    run(http.get(URL))
    assert sleeps == [7.0]


def test_502_is_retried():
    http, calls, _ = client_for([httpx.Response(502), httpx.Response(503), httpx.Response(200)])
    assert run(http.get(URL)).status_code == 200 and len(calls) == 3


def test_404_is_not_retried():
    http, calls, sleeps = client_for([httpx.Response(404)])
    with pytest.raises(HttpStatusError):
        run(http.get(URL))
    assert len(calls) == 1 and sleeps == []


def test_parsing_error_is_not_retried():
    http, calls, _ = client_for([httpx.Response(200, json={"unexpected": "shape"})])
    scraper = JsonApiScraper("Site", URL, "data.jobs", {"title": "title"}, http)
    with pytest.raises(ParseError) as exc:
        run(scraper.fetch_jobs())
    assert len(calls) == 1 and exc.value.status == ScrapeStatus.PARSE_ERROR
