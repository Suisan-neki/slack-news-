from __future__ import annotations

import logging
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Iterable, List

logger = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    link: str
    published: str | None = None
    summary: str | None = None
    published_at: datetime | None = None


def fetch_all_feeds(feed_urls: Iterable[str], timeout: int = 10) -> List[Article]:
    """複数の RSS/Atom フィードをまとめて取得する。"""
    articles: list[Article] = []
    for url in feed_urls:
        try:
            fetched = fetch_feed(url, timeout=timeout)
            logger.info("Fetched %d articles from %s", len(fetched), url)
            articles.extend(fetched)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to fetch %s: %s", url, exc)
    return articles


def fetch_feed(feed_url: str, timeout: int = 10) -> List[Article]:
    """単一フィードを取得し、Article のリストに変換する。"""
    with urllib.request.urlopen(feed_url, timeout=timeout) as response:
        content_type = response.headers.get_content_charset() or "utf-8"
        raw = response.read()
        text = raw.decode(content_type, errors="replace")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        logger.warning("XML parse error on %s: %s", feed_url, exc)
        return []

    entries = root.findall(".//item")
    if not entries:
        # Atom 形式対応
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    return [_element_to_article(entry) for entry in entries]


def _element_to_article(elem: ET.Element) -> Article:
    title = _text(elem, "title")
    link = _link(elem)
    published = (
        _text(elem, "pubDate")
        or _text(elem, "published")
        or _text(elem, "updated")
        or None
    )
    summary = (
        _text(elem, "description")
        or _text(elem, "summary")
        or _text(elem, "{http://www.w3.org/2005/Atom}summary")
        or None
    )
    published_at = _parse_datetime(published) if published else None
    return Article(
        title=title or "(no title)",
        link=link,
        published=published,
        summary=summary,
        published_at=published_at,
    )


def _text(elem: ET.Element, tag: str) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


def _link(elem: ET.Element) -> str:
    # RSS: <link>URL</link>
    link_text = _text(elem, "link")
    if link_text:
        return link_text
    # Atom: <link href="..."/>
    for child in elem.findall("link"):
        href = child.attrib.get("href")
        if href:
            return href
    return ""


def _parse_datetime(value: str) -> datetime | None:
    try:
        dt = parsedate_to_datetime(value)
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return dt
    except Exception:  # noqa: BLE001
        return None

