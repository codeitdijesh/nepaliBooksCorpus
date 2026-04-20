from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlparse

from lxml import html

from .utils import normalize_digits, normalize_space, parse_int

DETAIL_ID_RE = re.compile(r"/documents/detail/([0-9a-f\-]+)/")
PDF_URL_RE = re.compile(r"const\s+pdfUrl\s*=\s*'([^']+)'")
DOWNLOAD_ENDPOINT_RE = re.compile(r"url:\s*'(/documents/increment_download_count/[^']+/)'")
FILE_SIZE_RE = re.compile(r"File size:\s*([^\n<]+)")
VIEWS_RE = re.compile(r"([०१२३४५६७८९\d,]+)\s+Views")
REVIEWS_RE = re.compile(r"&nbsp;([०१२३४५६७८९\d,]+)\s+Reviews")
DEFAULT_LICENSE_RE = re.compile(
    r"Unless explicitly mentioned, all the contents on this website are licensed under\s*(.+?)\s*</a>",
    re.IGNORECASE | re.DOTALL,
)


def extract_doc_id(url: str) -> str | None:
    match = DETAIL_ID_RE.search(url)
    return match.group(1) if match else None


def parse_search_page(html_text: str, base_url: str) -> dict[str, object]:
    tree = html.fromstring(html_text)
    anchors = tree.xpath('//a[contains(@href, "/documents/detail/")]')
    results: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for anchor in anchors:
        href = anchor.get("href")
        title = normalize_space(anchor.text_content())
        if not href:
            continue
        doc_id = extract_doc_id(href)
        if not doc_id or doc_id in seen_ids:
            continue
        if not title:
            title = normalize_space(anchor.get("title"))
        results.append(
            {
                "doc_id": doc_id,
                "title": title,
                "detail_url": f"{base_url.rstrip('/')}{href}" if href.startswith("/") else href,
            }
        )
        seen_ids.add(doc_id)

    total_pages = 1
    for anchor in tree.xpath('//a[contains(@href, "page=")]'):
        href = anchor.get("href")
        if not href:
            continue
        page_value = parse_qs(urlparse(href).query).get("page")
        if page_value and page_value[0].isdigit():
            total_pages = max(total_pages, int(page_value[0]))

    return {"results": results, "total_pages": total_pages}


def parse_detail_page(html_text: str, detail_url: str) -> dict[str, object]:
    tree = html.fromstring(html_text)
    title = _extract_title(tree, html_text)
    doc_id = extract_doc_id(detail_url)
    metadata = _extract_metadata_table(tree)

    file_size_match = FILE_SIZE_RE.search(html_text)
    pdf_url_match = PDF_URL_RE.search(html_text)
    download_endpoint_match = DOWNLOAD_ENDPOINT_RE.search(html_text)
    default_license_match = DEFAULT_LICENSE_RE.search(html_text)

    keywords = metadata.get("Keywords", [])
    language = _metadata_value(metadata, "Language")
    publisher = _metadata_value(metadata, "Publisher")
    publication_year = _metadata_value(metadata, "Publication year")
    total_pages = parse_int(_metadata_value(metadata, "Total pages"))
    views = parse_int(VIEWS_RE.search(html_text).group(1)) if VIEWS_RE.search(html_text) else None
    reviews = parse_int(REVIEWS_RE.search(html_text).group(1)) if REVIEWS_RE.search(html_text) else None

    return {
        "doc_id": doc_id,
        "detail_url": detail_url,
        "title": title,
        "pdf_url": urljoin(detail_url, pdf_url_match.group(1)) if pdf_url_match else None,
        "download_count_url": urljoin(detail_url, download_endpoint_match.group(1)) if download_endpoint_match else None,
        "login_link_present": f"/accounts/login?next={detail_url.replace('https://pustakalaya.org', '')}" in html_text,
        "file_size_label": normalize_space(file_size_match.group(1)) if file_size_match else None,
        "views": views,
        "reviews": reviews,
        "language": language,
        "publisher": publisher,
        "publication_year": publication_year,
        "pages_total": total_pages,
        "keywords": keywords,
        "site_license_notice": normalize_space(default_license_match.group(1)) if default_license_match else None,
        "metadata": metadata,
    }


def _extract_title(tree: html.HtmlElement, html_text: str) -> str:
    title_text = normalize_space(" ".join(tree.xpath("//title/text()")))
    if "Document |" in title_text:
        return normalize_space(title_text.split("Document |", 1)[1])
    headings = tree.xpath("//h1/text() | //h2/text()")
    for heading in headings:
        heading = normalize_space(heading)
        if heading and "E-Pustakalaya" not in heading:
            return heading
    return normalize_space(title_text) or normalize_space(html_text[:200])


def _extract_metadata_table(tree: html.HtmlElement) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for row in tree.xpath("//tr[th and td]"):
        key = normalize_space(" ".join(row.xpath("./th//text()"))).rstrip(":")
        value_links = [normalize_space(text) for text in row.xpath("./td//a/text()") if normalize_space(text)]
        if value_links:
            metadata[key] = value_links
            continue
        value = normalize_space(" ".join(row.xpath("./td//text()")))
        metadata[key] = value
    return metadata


def _metadata_value(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
