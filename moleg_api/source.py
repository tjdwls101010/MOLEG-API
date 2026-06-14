"""Source adapters for law.go.kr."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from .errors import SourceApiError, UnsupportedFormatError


SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"
DEFAULT_TIMEOUT_SECONDS = 30
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
    ) -> None:
        self.oc = oc or os.environ.get("MOLEG_OC")
        if not self.oc:
            raise SourceApiError("MOLEG_OC is required for live law.go.kr calls")
        self.search_url = search_url
        self.service_url = service_url
        self.timeout_seconds = timeout_seconds

    def search(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.search_url, target, params)

    def service(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._call(self.service_url, target, params)

    def _call(self, url: str, target: str, params: dict[str, Any]) -> dict[str, Any]:
        query = {"OC": self.oc, "target": target, "type": "JSON", **params}
        request_url = url + "?" + urllib.parse.urlencode(query, doseq=True)
        request = urllib.request.Request(request_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                body = response.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
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


def mask_secret(text: str, secret: str | None) -> str:
    return text.replace(secret, "***") if secret else text
