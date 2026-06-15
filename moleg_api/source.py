"""Source adapters for law.go.kr."""

from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from .errors import RateLimitError, RetryExhaustedError, SourceApiError, UnsupportedFormatError


SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_DELAY_SECONDS = 0.5
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
DEFAULT_CA_FILE_CANDIDATES = (
    "/etc/ssl/cert.pem",
    "/opt/homebrew/etc/openssl@3/cert.pem",
    "/usr/local/etc/openssl@3/cert.pem",
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class MolegSource(Protocol):
    """Internal seam for source calls."""

    def search(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call a law.go.kr search target."""

    def service(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call a law.go.kr service/detail target."""


class LawGoKrClient:
    """JSON client for law.go.kr using `MOLEG_OC` by default."""

    def __init__(
        self,
        *,
        oc: str | None = None,
        search_url: str = SEARCH_URL,
        service_url: str = SERVICE_URL,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
        ssl_context: ssl.SSLContext | None = None,
        ca_file: str | None = None,
    ) -> None:
        self.oc = oc or os.environ.get("MOLEG_OC")
        if not self.oc:
            raise SourceApiError("MOLEG_OC is required for live law.go.kr calls")
        self.search_url = search_url
        self.service_url = service_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_delay_seconds = max(0.0, retry_delay_seconds)
        self.ssl_context = ssl_context or build_ssl_context(ca_file)

    def search(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.search_url, target, params)

    def service(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.service_url, target, params)

    def _call(self, url: str, target: str, params: dict[str, Any]) -> dict[str, Any]:
        query = {"OC": self.oc, "target": target, "type": "JSON", **params}
        request_url = url + "?" + urllib.parse.urlencode(query, doseq=True)
        for attempt in range(self.max_retries + 1):
            request = urllib.request.Request(request_url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout_seconds,
                    context=self.ssl_context,
                ) as response:
                    content_type = response.headers.get("Content-Type", "").lower()
                    body = response.read().decode("utf-8", errors="replace")
                    break
            except urllib.error.HTTPError as exc:
                if exc.code in RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        self._sleep_before_retry()
                        continue
                    message = http_error_message(exc, self.oc, target, attempt + 1)
                    if exc.code == 429:
                        raise RateLimitError(message) from exc
                    raise RetryExhaustedError(message) from exc
                raise SourceApiError(http_error_message(exc, self.oc, target, attempt + 1)) from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_retries:
                    self._sleep_before_retry()
                    continue
                message = (
                    f"law.go.kr retry exhausted for target {target} after {attempt + 1} attempt(s): "
                    f"{mask_secret(str(exc), self.oc)}"
                )
                if self.max_retries > 0:
                    raise RetryExhaustedError(message) from exc
                raise SourceApiError(mask_secret(str(exc), self.oc)) from exc

        if "json" not in content_type:
            snippet = mask_secret(body[:200].replace("\n", " "), self.oc)
            raise UnsupportedFormatError(
                f"law.go.kr returned non-JSON content ({content_type or 'unknown'}): {snippet}"
            )

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise SourceApiError("law.go.kr returned invalid JSON") from exc

    def _sleep_before_retry(self) -> None:
        if self.retry_delay_seconds:
            time.sleep(self.retry_delay_seconds)


def build_ssl_context(ca_file: str | None = None) -> ssl.SSLContext:
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)

    verify_paths = ssl.get_default_verify_paths()
    if verify_paths.cafile or verify_paths.capath:
        return ssl.create_default_context()

    for candidate in DEFAULT_CA_FILE_CANDIDATES:
        if os.path.exists(candidate):
            return ssl.create_default_context(cafile=candidate)

    return ssl.create_default_context()


def mask_secret(text: str, secret: str | None) -> str:
    return text.replace(secret, "***") if secret else text


def http_error_message(
    exc: urllib.error.HTTPError,
    secret: str | None,
    target: str,
    attempts: int,
) -> str:
    body = exc.read().decode("utf-8", errors="replace")
    snippet = mask_secret(body[:200].replace("\n", " "), secret)
    reason = mask_secret(str(exc.reason), secret)
    if exc.code == 429:
        label = "rate limited"
    elif exc.code in RETRYABLE_STATUS_CODES:
        label = "retry exhausted"
    else:
        label = "source HTTP error"
    return (
        f"law.go.kr {label} for target {target} after {attempts} attempt(s): "
        f"HTTP {exc.code} {reason}; {snippet}"
    )
