from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from fetcher import Article, fetch_all_feeds
from filter import filter_articles
from notifier import post_message
from storage import load_sent_urls, save_sent_urls

logger = logging.getLogger(__name__)


def _count_keyword_hits(articles: list[Article]) -> tuple[int, int, int]:
    med_kw = [kw.lower() for kw in config.MEDICAL_KEYWORDS]
    it_kw = [kw.lower() for kw in config.IT_KEYWORDS]
    med_count = it_count = both_count = 0
    for a in articles:
        text = f"{a.title} {a.summary or ''}".lower()
        has_med = any(kw in text for kw in med_kw)
        has_it = any(kw in text for kw in it_kw)
        med_count += has_med
        it_count += has_it
        both_count += has_med and has_it
    return med_count, it_count, both_count


def build_message(articles: list[Article], now: datetime) -> str:
    if not articles:
        return "🩺🤖 本時間帯の PR TIMES 医療×IT 新着はありませんでした。"

    header = f"🩺🤖 PR TIMES 医療×ITニュースまとめ（{now.strftime('%Y-%m-%d %H:%M JST')}）"
    lines = [header, ""]
    for article in articles:
        lines.append(f"・{article.title}")
        lines.append(f"  {article.link}")
        if article.published:
            lines.append(f"  公開: {article.published}")
        lines.append("")
    return "\n".join(lines).rstrip()


def sort_articles(articles: list[Article]) -> list[Article]:
    return sorted(
        articles,
        key=lambda a: a.published_at.timestamp() if a.published_at else float("-inf"),
        reverse=True,
    )


def run(dry_run: bool = False, storage_path: Path | None = None, max_items: int | None = None) -> int:
    storage_path = storage_path or config.SENT_URLS_PATH
    max_items = max_items or config.MAX_ARTICLES_PER_POST

    feed_urls = config.RSS_FEEDS
    if not feed_urls:
        logger.error("RSS_FEEDS が空です。PRTIMES_RSS_URLS を環境変数で設定するか config.py を編集してください。")
        return 1

    logger.info("Starting fetch for %d feed(s)", len(feed_urls))
    fetched = fetch_all_feeds(feed_urls, timeout=config.FETCH_TIMEOUT)
    if not fetched:
        logger.warning("フィードから記事を取得できませんでした。")
    else:
        med_count, it_count, both_count = _count_keyword_hits(fetched)
        logger.info("Keyword hits (before exclude): med=%d it=%d both=%d", med_count, it_count, both_count)

    filtered = filter_articles(
        fetched,
        medical_keywords=config.MEDICAL_KEYWORDS,
        it_keywords=config.IT_KEYWORDS,
        exclude_keywords=config.EXCLUDE_KEYWORDS,
    )
    filtered = sort_articles(filtered)

    sent_map = load_sent_urls(storage_path)
    new_articles = [a for a in filtered if a.link and a.link not in sent_map]
    if len(new_articles) > max_items:
        new_articles = new_articles[:max_items]

    now = datetime.now(timezone(timedelta(hours=9)))
    message = build_message(new_articles, now)

    logger.info("New articles: %d (after dedupe and limit)", len(new_articles))

    if dry_run:
        logger.info("Dry-run mode: message not sent to Slack.")
        print(message)
        return 0

    success = post_message(config.SLACK_WEBHOOK_URL, message, timeout=config.FETCH_TIMEOUT)
    if not success:
        logger.error("Slack 送信に失敗しました。")
        return 1

    if new_articles:
        timestamp = now.isoformat()
        for article in new_articles:
            sent_map[article.link] = timestamp
        save_sent_urls(sent_map, storage_path)
        logger.info("Saved %d sent URLs to %s", len(new_articles), storage_path)

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PR TIMES 医療×ITニュースをフィルタしてSlackに投稿します。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Slack に送らず標準出力にメッセージを表示する",
    )
    parser.add_argument(
        "--storage-path",
        type=Path,
        help=f"配信済みURL保存先 (デフォルト: {config.SENT_URLS_PATH})",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        help=f"1回の投稿件数上限 (デフォルト: {config.MAX_ARTICLES_PER_POST})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを有効にする",
    )
    return parser.parse_args()


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    if config.LOG_FILE:
        handlers = [
            logging.StreamHandler(),
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        ]
        logging.basicConfig(level=level, format=log_format, handlers=handlers)
    else:
        logging.basicConfig(level=level, format=log_format)


if __name__ == "__main__":
    args = parse_args()
    configure_logging(args.verbose)
    exit_code = run(
        dry_run=args.dry_run,
        storage_path=args.storage_path,
        max_items=args.max_items,
    )
    raise SystemExit(exit_code)
