from __future__ import annotations

import html
import logging
import re
import urllib.error
import urllib.request
from typing import List

from fetcher import Article

logger = logging.getLogger(__name__)


def fetch_medicaltech(timeout: int = 10) -> List[Article]:
    """医療テックニュースのトップページから記事を取得する。"""
    url = "https://medicaltech-news.com/"
    text = _get(url, timeout)
    if text is None:
        return []

    articles: list[Article] = []
    # H3 タイトルとリンクを抜く（トップページの最新一覧）
    for m in re.finditer(
        r'<h3[^>]*class="[^"]*item-ttl[^"]*"[^>]*>\\s*<a[^"]*href="([^"]+)"[^>]*>(.*?)</a>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        link = m.group(1).strip()
        title = _clean_html(m.group(2))
        # 直後の time datetime を拾う
        tail = text[m.end() : m.end() + 400]
        tm = re.search(r'<time[^>]*datetime="([^"]+)"', tail)
        published = tm.group(1) if tm else None
        articles.append(Article(title=title, link=link, published=published))
    logger.info("medicaltech-news: parsed %d articles", len(articles))
    return articles


def fetch_htwatch(timeout: int = 10) -> List[Article]:
    """ヘルステックウォッチのトップページから記事を取得する。"""
    url = "https://ht-watch.com/"
    text = _get(url, timeout)
    if text is None:
        return []

    articles: list[Article] = []
    # ピックアップ + 新着リストの記事 (<article> 内の h2 とリンク)
    for m in re.finditer(
        r"<article[^>]*>\\s*<a[^>]*href=\"([^\"]+)\"[^>]*>.*?<h2>(.*?)</h2>.*?(?:<p class=\"date\">(.*?)</p>)?",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        link = m.group(1).strip()
        title = _clean_html(m.group(2))
        published = _clean_html(m.group(3)) if m.group(3) else None
        articles.append(Article(title=title, link=link, published=published))
    logger.info("ht-watch: parsed %d articles", len(articles))
    return articles


def _get(url: str, timeout: int) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            charset = r.headers.get_content_charset() or "utf-8"
            return r.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
    except urllib.error.URLError as exc:
        logger.error("URL error fetching %s: %s", url, exc)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error fetching %s: %s", url, exc)
    return None


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()

