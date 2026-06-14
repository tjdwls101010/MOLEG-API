import io
import urllib.error

import pytest

from moleg_api import LawGoKrClient, RateLimitError, RetryExhaustedError, UnsupportedFormatError


class FakeResponse:
    def __init__(self, body: str, *, content_type: str = "application/json") -> None:
        self.body = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


def http_error(status: int, body: str = "") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://www.law.go.kr/DRF/lawSearch.do",
        code=status,
        msg="source failure",
        hdrs={},
        fp=io.BytesIO(body.encode("utf-8")),
    )


def test_law_client_retries_transient_failure_then_returns_json(monkeypatch):
    responses = [
        http_error(503),
        FakeResponse('{"LawSearch": {"law": []}}'),
    ]

    def fake_urlopen(request, timeout):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    assert client.search("eflaw", {"query": "자동차"}) == {"LawSearch": {"law": []}}
    assert responses == []


def test_law_client_raises_rate_limit_error_after_allowed_attempts(monkeypatch):
    responses = [
        http_error(429, "too many requests for secret-oc"),
        http_error(429, "still rate limited for secret-oc"),
    ]

    def fake_urlopen(request, timeout):
        raise responses.pop(0)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    with pytest.raises(RateLimitError) as exc_info:
        client.search("eflaw", {"query": "자동차"})

    assert "rate limited" in str(exc_info.value)
    assert "secret-oc" not in str(exc_info.value)
    assert responses == []


def test_law_client_raises_retry_exhausted_after_transient_errors(monkeypatch):
    responses = [
        http_error(503, "first failure for secret-oc"),
        urllib.error.URLError("network down for secret-oc"),
    ]

    def fake_urlopen(request, timeout):
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    with pytest.raises(RetryExhaustedError) as exc_info:
        client.service("eflaw", {"ID": "001234"})

    assert "retry exhausted" in str(exc_info.value)
    assert "secret-oc" not in str(exc_info.value)
    assert responses == []


def test_law_client_keeps_non_json_as_unsupported_format(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: FakeResponse("<html>not json</html>", content_type="text/html"),
    )

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    with pytest.raises(UnsupportedFormatError):
        client.search("eflaw", {"query": "자동차"})
