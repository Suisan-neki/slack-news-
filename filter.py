from __future__ import annotations

import logging
from typing import Iterable, List

from fetcher import Article

logger = logging.getLogger(__name__)


def filter_articles(
    articles: Iterable[Article],
    medical_keywords: Iterable[str],
    it_keywords: Iterable[str],
    exclude_keywords: Iterable[str] | None = None,
    exclude_domains: Iterable[str] | None = None,
) -> List[Article]:
    """医療系とIT系の両方のキーワードを含む記事だけに絞り込む。"""
    articles_list = list(articles)
    med_kw = [kw.lower() for kw in medical_keywords]
    it_kw = [kw.lower() for kw in it_keywords]
    ng_kw = [kw.lower() for kw in (exclude_keywords or [])]
    ng_domains = [dom.lower() for dom in (exclude_domains or [])]

    filtered: list[Article] = []
    for article in articles_list:
        # ドメインで除外
        if ng_domains and article.link:
            link_lower = article.link.lower()
            if any(dom in link_lower for dom in ng_domains):
                continue

        text = f"{article.title} {article.summary or ''}".lower()
        if ng_kw and any(kw in text for kw in ng_kw):
            continue
        
        # マッチした医療系キーワードを収集
        matched_med = [kw for kw in med_kw if kw in text]
        if not matched_med:
            continue
        
        # マッチしたIT系キーワードを収集
        matched_it = [kw for kw in it_kw if kw in text]
        if not matched_it:
            continue
        
        # マッチしたキーワードを記録（元の大文字小文字を保持）
        matched_keywords = []
        for kw in medical_keywords:
            if kw.lower() in matched_med:
                matched_keywords.append(kw)
        for kw in it_keywords:
            if kw.lower() in matched_it:
                matched_keywords.append(kw)
        
        # 記事のコピーを作成してキーワードを追加
        article_with_keywords = Article(
            title=article.title,
            link=article.link,
            published=article.published,
            summary=article.summary,
            published_at=article.published_at,
            matched_keywords=matched_keywords,
        )
        filtered.append(article_with_keywords)

    logger.info("Filtered %d articles -> %d", len(articles_list), len(filtered))
    return filtered
