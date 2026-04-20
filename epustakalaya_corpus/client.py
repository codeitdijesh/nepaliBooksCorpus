from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from .utils import RateLimiter, ensure_parent


class PustakalayaClient:
    def __init__(
        self,
        base_url: str = "https://pustakalaya.org",
        delay_seconds: float = 1.5,
        timeout_seconds: int = 30,
        user_agent: str = "epustakalaya-corpus/0.1 (+local research use)",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.rate_limiter = RateLimiter(delay_seconds)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def resolve_url(self, value: str) -> str:
        return urljoin(f"{self.base_url}/", value)

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        self.rate_limiter.wait()
        response = self.session.request(
            method=method,
            url=self.resolve_url(url),
            timeout=self.timeout_seconds,
            allow_redirects=True,
            **kwargs,
        )
        response.raise_for_status()
        return response

    def fetch_text(self, url: str) -> str:
        response = self.request("GET", url)
        return response.content.decode("utf-8", errors="replace")

    def fetch_search_page(self, page: int, query: str = "", form_filter: str = "", search_in: str = "all") -> str:
        response = self.request(
            "GET",
            "/search/",
            params={
                "page": page,
                "q": query,
                "form-filter": form_filter,
                "searchIn": search_in,
            },
        )
        return response.text

    def fetch_detail_page(self, detail_url: str) -> str:
        return self.fetch_text(detail_url)

    def probe_pdf(self, pdf_url: str) -> dict[str, Any]:
        try:
            response = self.request("HEAD", pdf_url)
        except requests.RequestException:
            response = self.request("GET", pdf_url, headers={"Range": "bytes=0-0"}, stream=True)
        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length")
        return {
            "final_url": response.url,
            "status_code": response.status_code,
            "content_type": content_type,
            "content_length": int(content_length) if content_length and content_length.isdigit() else None,
        }

    def download_file(self, url: str, destination: Path, overwrite: bool = False) -> dict[str, Any]:
        if destination.exists() and not overwrite:
            return {
                "path": str(destination),
                "bytes_written": destination.stat().st_size,
                "skipped_existing": True,
            }

        ensure_parent(destination)
        response = self.request("GET", url, stream=True)
        bytes_written = 0
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if not chunk:
                    continue
                handle.write(chunk)
                bytes_written += len(chunk)

        return {
            "path": str(destination),
            "bytes_written": bytes_written,
            "skipped_existing": False,
            "content_type": response.headers.get("Content-Type"),
        }
