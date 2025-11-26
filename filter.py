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
) -> List[Article]:
    """医療系とIT系の両方のキーワードを含む記事だけに絞り込む。"""
    articles_list = list(articles)
    med_kw = [kw.lower() for kw in medical_keywords]
    it_kw = [kw.lower() for kw in it_keywords]
    ng_kw = [kw.lower() for kw in (exclude_keywords or [])]

    filtered: list[Article] = []
    for article in articles_list:
        text = f"{article.title} {article.summary or ''}".lower()
        if ng_kw and any(kw in text for kw in ng_kw):
            continue
        if not any(kw in text for kw in med_kw):
            continue
        if not any(kw in text for kw in it_kw):
            continue
        filtered.append(article)

    logger.info("Filtered %d articles -> %d", len(articles_list), len(filtered))
    return filtered
