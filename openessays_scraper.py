#!/usr/bin/env python3
"""Download OpenEssays.org pages to local HTML files."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
from typing import List

import requests
from bs4 import BeautifulSoup
from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text

OPENESSAYS_HOSTS = {"openessays.org", "www.openessays.org"}
BASE_URL = "https://openessays.org"
ROBOTS_URL = f"{BASE_URL}/robots.txt"
DEFAULT_OUTPUT = pathlib.Path("data/raw")
DEFAULT_AGENT = "openessays-scraper/0.5 (+https://openrouter.ai/)"
DEFAULT_JSON = pathlib.Path("data/essays.json")
DEFAULT_PDF_DIR = pathlib.Path("data/pdfs")


@dataclass
class EssayMeta:
    slug: str
    essay_id: str | None = None
    school: str | None = None
    program: str | None = None
    essay_type: str | None = None
    program_type: str | None = None
    license: str | None = None
    source: str | None = None
    original_url: str | None = None
    excerpt: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "id": self.essay_id,
            "school": self.school,
            "program": self.program,
            "type": self.essay_type,
            "programType": self.program_type,
            "license": self.license,
            "source": self.source,
            "originalUrl": self.original_url,
            "excerpt": self.excerpt,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch pages from OpenEssays.org")
    parser.add_argument(
        "--url",
        dest="urls",
        action="append",
        help="URL or path to scrape (repeatable)",
    )
    parser.add_argument(
        "--urls-file",
        type=pathlib.Path,
        help="File containing one URL or path per line",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT,
        help=f"Directory for saved HTML (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between requests",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_AGENT,
        help="User-Agent header to send",
    )
    parser.add_argument(
        "--skip-robots",
        action="store_true",
        help="Skip robots.txt checks (not recommended)",
    )
    parser.add_argument(
        "--type",
        dest="types",
        action="append",
        help="Essay type filter to crawl (e.g. BACHELORS, MBA). Repeatable.",
    )
    parser.add_argument(
        "--listing-file",
        dest="listing_files",
        action="append",
        type=pathlib.Path,
        help="Existing HTML listing file to extract essay slugs from",
    )
    parser.add_argument(
        "--download-essays",
        action="store_true",
        help="After collecting slugs, download each /essay/<slug> page",
    )
    parser.add_argument(
        "--max-essays",
        type=int,
        help="Limit the number of essay detail pages to download",
    )
    parser.add_argument(
        "--download-originals",
        action="store_true",
        help="Also download the external originalUrl for each essay entry",
    )
    parser.add_argument(
        "--json-output",
        type=pathlib.Path,
        default=DEFAULT_JSON,
        help=f"Where to store extracted essay text as JSON (default: {DEFAULT_JSON})",
    )
    parser.add_argument(
        "--pdf-dir",
        type=pathlib.Path,
        default=DEFAULT_PDF_DIR,
        help="Directory for storing raw PDFs pulled from Google Drive (default: data/pdfs)",
    )
    return parser.parse_args()


def collect_urls(args: argparse.Namespace) -> List[str]:
    raw: List[str] = []
    if args.urls:
        raw.extend(args.urls)
    if args.urls_file:
        if not args.urls_file.exists():
            raise FileNotFoundError(f"URLs file '{args.urls_file}' not found")
        raw.extend(line.strip() for line in args.urls_file.read_text().splitlines())

    urls: List[str] = []
    for item in raw:
        if not item:
            continue
        url = normalize_url(item)
        urls.append(url)

    if not urls:
        raise ValueError("Provide at least one --url or a non-empty --urls-file")

    return urls


def normalize_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if not parsed.scheme:
        value = urllib.parse.urljoin(BASE_URL, value)
        parsed = urllib.parse.urlparse(value)
    if parsed.netloc not in OPENESSAYS_HOSTS:
        raise ValueError(f"Only OpenEssays URLs are supported: '{value}'")
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme: '{parsed.scheme}'")
    return urllib.parse.urlunparse(parsed)


def load_robots(user_agent: str) -> urllib.robotparser.RobotFileParser | None:
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(ROBOTS_URL)
    try:
        parser.read()
    except Exception as exc:  # pragma: no cover - best-effort guard
        print(f"Warning: failed to load robots.txt ({exc}); continuing", file=sys.stderr)
        return None
    return parser


def is_allowed(url: str, user_agent: str, robots: urllib.robotparser.RobotFileParser | None) -> bool:
    if robots is None:
        return True
    return robots.can_fetch(user_agent, url)


def output_path(url: str, base_dir: pathlib.Path) -> pathlib.Path:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lstrip("/")
    if not path:
        path = "index"
    if path.endswith("/"):
        path = path.rstrip("/") + "_index"
    safe_path = path.replace("/", "_")
    if parsed.query:
        safe_query = parsed.query.replace("/", "_").replace("&", "+")
        safe_path = f"{safe_path}_{safe_query}"
    return (base_dir / parsed.netloc / f"{safe_path}.html").resolve()


def fetch_and_save(
    url: str,
    session: requests.Session,
    output_dir: pathlib.Path,
    capture_text: bool = False,
) -> tuple[pathlib.Path, str | None]:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    destination = output_path(url, output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    text = response.text if capture_text else None
    return destination, text


def extract_text_content(html: str | None) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    target = soup.find("article")
    if target:
        text = target.get_text("\n", strip=True)
        if text:
            return text
    body = soup.body
    if body:
        return body.get_text("\n", strip=True)
    return soup.get_text("\n", strip=True)


def build_record(
    meta: EssayMeta,
    text: str,
    destination: pathlib.Path,
    downloaded_from: str,
    url: str,
) -> dict:
    record = meta.to_dict()
    record.update(
        {
            "text": text,
            "downloadedFrom": downloaded_from,
            "downloadUrl": url,
            "savedHtml": str(destination),
        }
    )
    return record


def maybe_append_record(
    records: List[dict],
    meta: EssayMeta,
    text: str | None,
    destination: pathlib.Path | None,
    source_label: str,
    url: str,
) -> None:
    if destination is None or not text:
        return
    records.append(build_record(meta, text, destination, source_label, url))


def extract_text_from_pdf(data: bytes) -> str:
    try:
        return pdf_extract_text(BytesIO(data))
    except Exception:  # pragma: no cover - pdf edge cases
        return ""


def extract_text_from_docx(data: bytes) -> str:
    try:
        doc = Document(BytesIO(data))
    except Exception:  # pragma: no cover - corrupt files
        return ""
    lines = [para.text.strip() for para in doc.paragraphs if para.text and para.text.strip()]
    return "\n\n".join(lines)


def _update_query_params(url: str, extra: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(url)
    query = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query.update({k: v for k, v in extra.items() if v is not None})
    new_query = urllib.parse.urlencode(query)
    return urllib.parse.urlunparse(parsed._replace(query=new_query))


def _drive_confirm_token(response: requests.Response) -> str | None:
    for key, value in response.cookies.items():
        if key.startswith("download_warning") and value:
            return value
    text = response.text
    token_patterns = [
        r"confirm=([0-9A-Za-z_]+)&",
        r'name=\"confirm\" value=\"([0-9A-Za-z_]+)\"',
    ]
    for pattern in token_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _ensure_drive_download(
    session: requests.Session,
    url: str,
    response: requests.Response,
) -> requests.Response:
    data = response.content
    content_type = (response.headers.get("Content-Type") or "").lower()
    if data.startswith(b"%PDF") or data[:4] == b"PK\x03\x04":
        return response
    if "text/html" not in content_type:
        return response
    token = _drive_confirm_token(response)
    if not token:
        return response
    confirm_url = _update_query_params(url, {"confirm": token})
    new_response = session.get(confirm_url, timeout=60)
    new_response.raise_for_status()
    return new_response


def resolve_external_target(url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path

    if host in {"x.com", "twitter.com"}:
        return (f"https://r.jina.ai/{url}", "twitter-proxy")

    if host == "docs.google.com" and "/document/" in path:
        parts = [part for part in path.split("/") if part]
        try:
            idx = parts.index("d")
            doc_id = parts[idx + 1]
        except (ValueError, IndexError):
            doc_id = None
        if doc_id:
            return (
                f"https://docs.google.com/document/d/{doc_id}/export?format=txt",
                "google-doc",
            )

    if host == "drive.google.com":
        file_id = None
        match = re.search(r"/d/([^/]+)/", path)
        if match:
            file_id = match.group(1)
        if not file_id:
            query = urllib.parse.parse_qs(parsed.query)
            if "id" in query:
                file_id = query["id"][0]
        if file_id:
            return (
                f"https://drive.google.com/uc?export=download&id={file_id}",
                "google-drive",
            )

    if host == "github.com":
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 4 and parts[2] == "blob":
            user, repo, _, branch, *rest = parts
            raw_path = "/".join(rest)
            return (
                f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{raw_path}",
                "github-raw",
            )

    if host == "raw.githubusercontent.com":
        return (url, "github-raw")

    if host in {"gist.github.com", "gist.githubusercontent.com"}:
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2:
            user, gist_id = parts[:2]
            return (
                f"https://gist.githubusercontent.com/{user}/{gist_id}/raw",
                "gist-raw",
            )

    return (url, host or "external")


def extract_text_from_response(
    url: str,
    response: requests.Response,
) -> str:
    content_type = (response.headers.get("Content-Type") or "").lower()
    data = response.content

    if data.startswith(b"%PDF"):
        return extract_text_from_pdf(data)

    if data[:4] == b"PK\x03\x04":
        return extract_text_from_docx(data)

    if "application/pdf" in content_type or url.lower().endswith(".pdf"):
        return extract_text_from_pdf(data)

    if (
        "wordprocessingml" in content_type
        or url.lower().endswith(".docx")
        or "application/vnd.openxmlformats-officedocument" in content_type
    ):
        return extract_text_from_docx(data)

    if "text/plain" in content_type or "text/markdown" in content_type or url.lower().endswith(".md"):
        try:
            return data.decode(response.encoding or "utf-8", errors="ignore")
        except Exception:
            return data.decode("utf-8", errors="ignore")

    html = response.text
    return extract_text_content(html)


def _download_original(
    meta: EssayMeta,
    session: requests.Session,
    args: argparse.Namespace,
    robots: urllib.robotparser.RobotFileParser | None,
) -> tuple[pathlib.Path | None, str | None, str]:
    if not meta.original_url:
        print(f"No original URL recorded for {meta.slug}")
        return None, None, ""
    parsed = urllib.parse.urlparse(meta.original_url)
    if parsed.scheme not in {"http", "https"}:
        print(f"Skipping {meta.original_url} (unsupported scheme)")
        return None, None, ""
    if parsed.netloc in OPENESSAYS_HOSTS and robots and not is_allowed(
        meta.original_url, args.user_agent, robots
    ):
        print(f"Skipping original {meta.original_url} (disallowed by robots.txt)")
        return None, None, ""

    final_url, label = resolve_external_target(meta.original_url)

    try:
        response = session.get(final_url, timeout=60)
        response.raise_for_status()
        if label == "google-drive":
            response = _ensure_drive_download(session, final_url, response)
            final_url = response.url
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        print(
            f"HTTP error for original {final_url} ({status})",
            file=sys.stderr,
        )
        return None, None, label
    except requests.RequestException as exc:
        print(f"Request failed for original {final_url}: {exc}", file=sys.stderr)
        return None, None, label
    data = response.content

    if (
        args.pdf_dir
        and label == "google-drive"
        and data.startswith(b"%PDF")
    ):
        args.pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = args.pdf_dir / f"{meta.slug}.pdf"
        pdf_path.write_bytes(data)
        print(f"Saved PDF for {meta.slug} -> {pdf_path}")

    destination = output_path(final_url, args.output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    text = extract_text_from_response(final_url, response)
    print(f"Saved original for {meta.slug} -> {destination}")
    return destination, text, label or "original"


def extract_metadata_from_listing(html: str) -> List[EssayMeta]:
    if not html:
        return []
    key = '\\"essays\\"'
    idx = html.find(key)
    if idx == -1:
        return []
    start = html.find('[', idx)
    if start == -1:
        return []
    depth = 0
    end = None
    for offset, ch in enumerate(html[start:], start):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end = offset
                break
    if end is None:
        return []
    frag = html[start : end + 1]
    try:
        decoded = bytes(frag, "utf-8").decode("unicode_escape")
        entries = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):  # pragma: no cover
        return []

    metas: OrderedDict[str, EssayMeta] = OrderedDict()
    for entry in entries:
        slug = entry.get("urlSlug")
        if not slug:
            continue
        metas.setdefault(
            slug,
            EssayMeta(
                slug=slug,
                essay_id=entry.get("id"),
                school=entry.get("school"),
                program=entry.get("program"),
                essay_type=entry.get("type"),
                program_type=entry.get("programType"),
                license=entry.get("license"),
                source=entry.get("source"),
                original_url=entry.get("originalUrl"),
                excerpt=entry.get("excerpt"),
                created_at=entry.get("createdAt"),
                updated_at=entry.get("updatedAt"),
            ),
        )
    return list(metas.values())


def collect_metadata(
    args: argparse.Namespace,
    session: requests.Session,
) -> List[EssayMeta]:
    html_blobs: List[str] = []

    for listing in args.listing_files or []:
        if not listing.exists():
            raise FileNotFoundError(f"Listing file '{listing}' not found")
        html_blobs.append(listing.read_text())

    for essay_type in args.types or []:
        query = {"type": essay_type}
        listing_url = f"{BASE_URL}/?{urllib.parse.urlencode(query)}"
        _, html = fetch_and_save(listing_url, session, args.output_dir, capture_text=True)
        if html is None:
            continue
        html_blobs.append(html)

    metas: OrderedDict[str, EssayMeta] = OrderedDict()
    for html in html_blobs:
        for meta in extract_metadata_from_listing(html):
            metas.setdefault(meta.slug, meta)

    return list(metas.values())


def main() -> int:
    args = parse_args()

    urls: List[str] = []
    if args.urls or args.urls_file:
        try:
            urls = collect_urls(args)
        except (ValueError, FileNotFoundError) as exc:
            print(exc, file=sys.stderr)
            return 1
    elif not (args.types or args.listing_files):
        print("Provide --url/--urls-file, --type, or --listing-file so there is work to do", file=sys.stderr)
        return 1

    robots = None
    if not args.skip_robots:
        robots = load_robots(args.user_agent)

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    metas: List[EssayMeta] = []
    records: List[dict] = []
    if args.types or args.listing_files:
        try:
            metas = collect_metadata(args, session)
        except (FileNotFoundError, requests.HTTPError, requests.RequestException) as exc:
            print(f"Failed to collect essay listings: {exc}", file=sys.stderr)
            return 1
        if metas:
            print(f"Found {len(metas)} essay entries from listings")
    elif args.download_essays or args.download_originals:
        print("--download-essays/--download-originals require --type or --listing-file", file=sys.stderr)
        return 1

    for idx, url in enumerate(urls):
        if robots and not is_allowed(url, args.user_agent, robots):
            print(f"Skipping {url} (disallowed by robots.txt)")
            continue
        try:
            destination, _ = fetch_and_save(url, session, args.output_dir)
        except requests.HTTPError as exc:
            print(f"HTTP error for {url}: {exc.response.status_code}", file=sys.stderr)
            continue
        except requests.RequestException as exc:
            print(f"Request failed for {url}: {exc}", file=sys.stderr)
            continue
        print(f"Saved {url} -> {destination}")
        if idx < len(urls) - 1:
            time.sleep(max(0.0, args.delay))

    if args.download_essays and metas:
        limit = args.max_essays if args.max_essays and args.max_essays > 0 else None
        print(
            f"Downloading OpenEssays detail pages for {len(metas)} entries"
            + (f" (limit {limit})" if limit else "")
        )
        for idx, meta in enumerate(metas):
            if limit is not None and idx >= limit:
                break
            url = f"{BASE_URL}/essay/{meta.slug}"
            if robots and not is_allowed(url, args.user_agent, robots):
                print(f"Skipping essay {meta.slug} (disallowed by robots.txt)")
                continue
            try:
                destination, html = fetch_and_save(
                    url, session, args.output_dir, capture_text=True
                )
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else "?"
                print(
                    f"HTTP error for essay {meta.slug}: {status}",
                    file=sys.stderr,
                )
                if (
                    status == 404
                    and meta.original_url
                    and args.download_originals
                ):
                    dest, original_text, label = _download_original(
                        meta, session, args, robots
                    )
                    maybe_append_record(
                        records,
                        meta,
                        original_text,
                        dest,
                        f"original:{label}" if label else "original",
                        meta.original_url or "",
                    )
                continue
            except requests.RequestException as exc:
                print(f"Request failed for essay {meta.slug}: {exc}", file=sys.stderr)
                continue
            print(f"Saved essay {meta.slug} -> {destination}")
            text = extract_text_content(html)
            maybe_append_record(records, meta, text, destination, "openessays", url)
            if limit is None or idx < limit - 1:
                time.sleep(max(0.0, args.delay))

    if args.download_originals and metas and not args.download_essays:
        limit = args.max_essays if args.max_essays and args.max_essays > 0 else None
        print(
            f"Downloading originalUrl targets for {len(metas)} entries"
            + (f" (limit {limit})" if limit else "")
        )
        for idx, meta in enumerate(metas):
            if limit is not None and idx >= limit:
                break
            dest, text, label = _download_original(meta, session, args, robots)
            maybe_append_record(
                records,
                meta,
                text,
                dest,
                f"original:{label}" if label else "original",
                meta.original_url or "",
            )
            if limit is None or idx < limit - 1:
                time.sleep(max(0.0, args.delay))

    if args.json_output and records:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(records, indent=2))
        print(f"Wrote {len(records)} records to {args.json_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
