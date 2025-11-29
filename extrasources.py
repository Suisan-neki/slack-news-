from __future__ import annotations

import html
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import List
from urllib.parse import urljoin

from fetcher import Article

logger = logging.getLogger(__name__)


def fetch_medicaltech(timeout: int = 10) -> List[Article]:
    """医療テックニュースのトップページから記事を取得する。"""
    url = "https://medicaltech-news.com/"
    text = _get(url, timeout)
    if text is None:
        return []

    articles: list[Article] = []
    
    # 方法1: 正規表現で抽出（修正版）
    # H3 タイトルとリンクを抜く（トップページの最新一覧）
    # 正規表現のバグ修正: \\s* -> \s*
    pattern = r'<h3[^>]*class="[^"]*item-ttl[^"]*"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
        link = m.group(1).strip()
        title = _clean_html(m.group(2))
        if not link or not title:
            continue
        
        # 相対URLを絶対URLに変換
        if not link.startswith("http"):
            link = urljoin(url, link)
        
        # 直後の time datetime を拾う
        tail = text[m.end() : m.end() + 400]
        tm = re.search(r'<time[^>]*datetime="([^"]+)"', tail)
        published = tm.group(1) if tm else None
        
        # 概要（description）を取得（記事ページから取得を試みる）
        summary = _fetch_summary_from_page(link, timeout)
        
        # published文字列からpublished_atを設定
        published_at = _parse_datetime(published) if published else None
        
        articles.append(Article(title=title, link=link, published=published, summary=summary, published_at=published_at))
    
    # 方法2: より柔軟なパターンでフォールバック
    if not articles:
        # より広範囲なパターンで検索
        pattern2 = r'<h[23][^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h[23]>'
        for m in re.finditer(pattern2, text, flags=re.IGNORECASE | re.DOTALL):
            link = m.group(1).strip()
            title = _clean_html(m.group(2))
            if not link or not title or len(title) < 5:  # 短すぎるタイトルは除外
                continue
            if not link.startswith("http"):
                link = urljoin(url, link)
            # 概要を取得
            summary = _fetch_summary_from_page(link, timeout)
            articles.append(Article(title=title, link=link, published=None, summary=summary, published_at=None))
    
    logger.info("medicaltech-news: parsed %d articles", len(articles))
    return articles


def fetch_htwatch(timeout: int = 10) -> List[Article]:
    """ヘルステックウォッチのトップページから記事を取得する。"""
    url = "https://ht-watch.com/"
    text = _get(url, timeout)
    if text is None:
        return []

    articles: list[Article] = []
    
    # 方法1: 正規表現で抽出（修正版）
    # 正規表現のバグ修正: \\s* -> \s*
    pattern = r'<article[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>.*?<h2>(.*?)</h2>.*?(?:<p[^>]*class="[^"]*date[^"]*"[^>]*>(.*?)</p>)?'
    for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
        link = m.group(1).strip()
        title = _clean_html(m.group(2))
        if not link or not title:
            continue
        
        # 相対URLを絶対URLに変換
        if not link.startswith("http"):
            link = urljoin(url, link)
        
        published = _clean_html(m.group(3)) if m.group(3) else None
        
        # 概要（description）を取得（記事ページから取得を試みる）
        summary = _fetch_summary_from_page(link, timeout)
        
        # published文字列からpublished_atを設定
        published_at = _parse_datetime(published) if published else None
        
        articles.append(Article(title=title, link=link, published=published, summary=summary, published_at=published_at))
    
    # 方法2: より柔軟なパターンでフォールバック
    if not articles:
        # articleタグ内のリンクとh2を探す
        pattern2 = r'<article[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>.*?<h2[^>]*>(.*?)</h2>'
        for m in re.finditer(pattern2, text, flags=re.IGNORECASE | re.DOTALL):
            link = m.group(1).strip()
            title = _clean_html(m.group(2))
            if not link or not title or len(title) < 5:
                continue
            if not link.startswith("http"):
                link = urljoin(url, link)
            # 概要を取得
            summary = _fetch_summary_from_page(link, timeout)
            articles.append(Article(title=title, link=link, published=None, summary=summary, published_at=None))
    
    logger.info("ht-watch: parsed %d articles", len(articles))
    return articles


def fetch_google_news(timeout: int = 10) -> List[Article]:
    """Googleニュースから医療×IT関連の記事を取得する（RSSフィードを使用）。"""
    # GoogleニュースのRSSフィードを使用（医療×ITで検索）
    import urllib.parse
    from fetcher import fetch_feed
    
    query = "医療 IT"
    rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=ja&gl=JP&ceid=JP:ja"
    
    try:
        articles = fetch_feed(rss_url, timeout=timeout)
        logger.info("google-news: fetched %d articles from RSS", len(articles))
        return articles
    except Exception as exc:
        logger.exception("Failed to fetch Google News RSS: %s", exc)
        return []


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


def _fetch_summary_from_page(link: str, timeout: int) -> str | None:
    """記事ページからsummary（description）を取得する共通関数。"""
    try:
        article_text = _get(link, timeout)
        if not article_text:
            return None
        
        # まずmeta description を探す
        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', article_text, re.IGNORECASE)
        if not desc_match:
            # og:description を探す
            desc_match = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', article_text, re.IGNORECASE)
        
        if desc_match:
            meta_desc = _clean_html(desc_match.group(1))
            # サイト全体の説明文でないかチェック
            if len(meta_desc) > 20 and "クリッピングサイト" not in meta_desc and "HealthTechWatchサイトは" not in meta_desc:
                return meta_desc
        
        # meta descriptionが取得できない、またはサイト全体の説明の場合は、記事本文から抽出を試みる
        # entryクラス内の本文を探す
        entry_match = re.search(r'<article[^>]*class=["\']entry["\'][^>]*>(.*?)</article>', article_text, re.DOTALL | re.IGNORECASE)
        if entry_match:
            entry_content = entry_match.group(1)
            # 最初の数個の<p>タグから本文を抽出
            paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', entry_content, re.DOTALL)
            # 長い段落を探す（meta情報は短い）
            for p in paragraphs:
                clean_p = _clean_html(p).strip()
                if len(clean_p) > 50:  # 50文字以上の段落を本文とみなす
                    return clean_p
        
        # entryクラスがない場合、一般的な本文領域を探す
        # main、content、post-contentなどのクラスを探す
        for class_name in ['main', 'content', 'post-content', 'article-body', 'entry-content']:
            content_match = re.search(
                rf'<div[^>]*class=["\'][^"]*{class_name}[^"]*["\'][^>]*>(.*?)</div>',
                article_text,
                re.DOTALL | re.IGNORECASE
            )
            if content_match:
                content = content_match.group(1)
                paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
                for p in paragraphs:
                    clean_p = _clean_html(p).strip()
                    if len(clean_p) > 50:
                        return clean_p
        
        # 最後の手段: 最初の長い<p>タグを探す
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', article_text, re.DOTALL)
        for p in paragraphs:
            clean_p = _clean_html(p).strip()
            if len(clean_p) > 50:
                return clean_p
                
    except Exception:
        pass  # 概要の取得に失敗しても続行
    
    return None


def _parse_datetime(value: str) -> datetime | None:
    """日時文字列をdatetimeオブジェクトに変換する。"""
    try:
        dt = parsedate_to_datetime(value)
        if dt and dt.tzinfo is None:
            # タイムゾーン情報がない場合はJSTと仮定
            return dt.replace(tzinfo=timezone(timedelta(hours=9)))
        return dt
    except Exception:  # noqa: BLE001
        return None
