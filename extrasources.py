from __future__ import annotations

import html
import logging
import re
import urllib.error
import urllib.request
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
        
        articles.append(Article(title=title, link=link, published=published))
    
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
            articles.append(Article(title=title, link=link, published=None))
    
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
        articles.append(Article(title=title, link=link, published=published))
    
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
            articles.append(Article(title=title, link=link, published=None))
    
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


def fetch_note(timeout: int = 10) -> List[Article]:
    """note.comから医療×IT関連の記事を取得する。"""
    import urllib.parse
    
    articles: list[Article] = []
    
    # note.comはJavaScriptで動的にコンテンツを読み込むため、
    # 複数のアプローチを試す
    
    # 方法1: タグページから取得を試みる（医療、IT、医療DXなどのタグ）
    tags = ["医療", "IT", "医療DX", "ヘルステック", "デジタルヘルス"]
    for tag in tags:
        tag_url = f"https://note.com/hashtag/{urllib.parse.quote(tag)}"
        text = _get(tag_url, timeout)
        if text is None:
            continue
        
        # note.comの記事リンクパターンを探す
        # /n/で始まる記事URLを探す
        pattern = r'href="(/n/[a-zA-Z0-9]+)"'
        for m in re.finditer(pattern, text):
            link = m.group(1).strip()
            if link:
                full_link = urljoin("https://note.com", link)
                # タイトルを取得するために記事ページにアクセス
                article_text = _get(full_link, timeout)
                if article_text:
                    # タイトルを抽出
                    title_match = re.search(r'<title[^>]*>(.*?)</title>', article_text, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        title = _clean_html(title_match.group(1))
                        # " | note"などのサフィックスを除去
                        title = re.sub(r'\s*\|\s*note.*$', '', title, flags=re.IGNORECASE)
                        if title and len(title) > 5:
                            # 重複チェック
                            if not any(a.link == full_link for a in articles):
                                articles.append(Article(title=title, link=full_link, published=None))
        
        # 10件取得したら次のタグへ
        if len(articles) >= 10:
            break
    
    # 方法2: 検索結果ページから取得を試みる（User-Agentを設定）
    if len(articles) < 5:
        query = "医療 IT"
        search_url = f"https://note.com/search?q={urllib.parse.quote(query)}&mode=search"
        
        # User-Agentを設定してリクエスト
        try:
            req = urllib.request.Request(search_url)
            req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                charset = r.headers.get_content_charset() or "utf-8"
                text = r.read().decode(charset, errors="replace")
            
            # 記事リンクを探す
            pattern = r'href="(/n/[a-zA-Z0-9]+)"'
            for m in re.finditer(pattern, text):
                link = m.group(1).strip()
                if link:
                    full_link = urljoin("https://note.com", link)
                    # 重複チェック
                    if not any(a.link == full_link for a in articles):
                        # タイトルを取得するために記事ページにアクセス
                        article_text = _get(full_link, timeout)
                        if article_text:
                            title_match = re.search(r'<title[^>]*>(.*?)</title>', article_text, re.IGNORECASE | re.DOTALL)
                            if title_match:
                                title = _clean_html(title_match.group(1))
                                title = re.sub(r'\s*\|\s*note.*$', '', title, flags=re.IGNORECASE)
                                if title and len(title) > 5:
                                    articles.append(Article(title=title, link=full_link, published=None))
                                    if len(articles) >= 20:  # 最大20件
                                        break
        except Exception as exc:
            logger.debug("Failed to fetch note.com search: %s", exc)
    
    logger.info("note.com: parsed %d articles", len(articles))
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

