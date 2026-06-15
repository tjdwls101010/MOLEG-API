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

    def fake_urlopen(request, timeout, context=None):
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

    def fake_urlopen(request, timeout, context=None):
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

    def fake_urlopen(request, timeout, context=None):
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
        lambda request, timeout, context=None: FakeResponse("<html>not json</html>", content_type="text/html"),
    )

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    with pytest.raises(UnsupportedFormatError):
        client.search("eflaw", {"query": "자동차"})


def test_law_client_returns_html_for_html_only_search(monkeypatch):
    requested_urls = []

    def fake_urlopen(request, timeout, context=None):
        requested_urls.append(request.full_url)
        return FakeResponse("<html>history</html>", content_type="text/html;charset=UTF-8")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    assert client.search_html("lsHistory", {"query": "건축법"}) == "<html>history</html>"
    assert "type=HTML" in requested_urls[0]


def test_law_client_rejects_non_html_for_html_only_search(monkeypatch):
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout, context=None: FakeResponse('{"not": "html"}', content_type="application/json"),
    )

    client = LawGoKrClient(oc="secret-oc", max_retries=1, retry_delay_seconds=0)

    with pytest.raises(UnsupportedFormatError):
        client.search_html("lsHistory", {"query": "건축법"})


def test_law_client_passes_ssl_context_to_urlopen(monkeypatch):
    contexts = []
    ssl_context = object()

    def fake_urlopen(request, timeout, context=None):
        contexts.append(context)
        return FakeResponse('{"LawSearch": {"law": []}}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = LawGoKrClient(oc="secret-oc", ssl_context=ssl_context)

    client.search("eflaw", {"query": "자동차"})

    assert contexts == [ssl_context]


def test_law_client_uses_fallback_ca_file_when_python_has_no_default(monkeypatch):
    class VerifyPaths:
        cafile = None
        capath = None

    created_with = []
    ssl_context = object()

    monkeypatch.setattr("moleg_api.source.ssl.get_default_verify_paths", lambda: VerifyPaths())
    monkeypatch.setattr("moleg_api.source.DEFAULT_CA_FILE_CANDIDATES", ("/tmp/project-ca.pem",))
    monkeypatch.setattr("moleg_api.source.os.path.exists", lambda path: path == "/tmp/project-ca.pem")

    def fake_create_default_context(*, cafile=None):
        created_with.append(cafile)
        return ssl_context

    monkeypatch.setattr("moleg_api.source.ssl.create_default_context", fake_create_default_context)

    client = LawGoKrClient(oc="secret-oc")

    assert client.ssl_context is ssl_context
    assert created_with == ["/tmp/project-ca.pem"]


def test_law_client_reads_moleg_oc_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("MOLEG_OC", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n# local live key\nMOLEG_OC='file-secret'\nOTHER=value\n",
        encoding="utf-8",
    )

    client = LawGoKrClient(ssl_context=object())

    assert client.oc == "file-secret"


def test_law_client_env_file_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv("MOLEG_OC", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("MOLEG_OC=file-secret\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text('MOLEG_OC=\"local-secret\"\n', encoding="utf-8")

    client = LawGoKrClient(ssl_context=object())

    assert client.oc == "local-secret"


def test_law_client_process_env_wins_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MOLEG_OC", "process-secret")
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.local").write_text("MOLEG_OC=local-secret\n", encoding="utf-8")

    client = LawGoKrClient(ssl_context=object())

    assert client.oc == "process-secret"
