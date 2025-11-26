"""
設定値とキーワード定義。

必要に応じて環境変数で上書きできます:
- SLACK_WEBHOOK_URL: Slack Incoming Webhook のURL
- PRTIMES_RSS_URLS: カンマ区切りの RSS URL 一覧
"""
from __future__ import annotations

import os
from pathlib import Path

# Slack Webhook
SLACK_WEBHOOK_URL: str | None = os.environ.get("SLACK_WEBHOOK_URL")

# RSS URL（カンマ区切りの環境変数で上書き可能）
_rss_env = [
    url.strip()
    for url in os.environ.get("PRTIMES_RSS_URLS", "").split(",")
    if url.strip()
]

# デフォルトは空。運用時に必ず RSS URL を設定してください。
DEFAULT_RSS_FEEDS: list[str] = []
RSS_FEEDS: list[str] = _rss_env or DEFAULT_RSS_FEEDS

# キーワード定義（編集しやすいようにここでまとめる）
MEDICAL_KEYWORDS: list[str] = [
    "医療",
    "ヘルスケア",
    "診療",
    "病院",
    "歯科",
    "看護",
    "クリニック",
    "製薬",
]

IT_KEYWORDS: list[str] = [
    "AI",
    "IT",
    "DX",
    "デジタル",
    "電子カルテ",
    "システム",
    "SaaS",
    "クラウド",
    "アプリ",
]

EXCLUDE_KEYWORDS: list[str] = [
    "美容整形",
    "ダイエットサプリ",
    "エステ",
]

# 1回あたりの投稿件数上限（Slack 文字数制限を考慮）
MAX_ARTICLES_PER_POST: int = 20

# RSS 取得タイムアウト（秒）
FETCH_TIMEOUT: int = 10

# 配信済みURLの保存先
DATA_DIR = Path("data")
SENT_URLS_PATH = DATA_DIR / "sent_urls.json"

