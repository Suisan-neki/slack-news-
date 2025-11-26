# 医療×ITニュース自動配信システム

PR TIMES の医療×IT領域ニュースを抽出し、Slack に1日3回まとめて投稿するためのツールです。

## 機能概要
- PR TIMES のRSSを取得し、タイトル/概要に「医療系キーワード」かつ「IT系キーワード」を含む記事のみ抽出
- 過去送信済みURLをJSONで保持し、重複送信を防止
- 抽出記事を1つのメッセージにまとめて Slack Incoming Webhook へ投稿
- 件数が多い場合は上限（デフォルト20件）までに制限
- 記事がない場合は「新着なし」を送信

## セットアップ
1. `.env.example` を `.env` にコピーし、Slack Webhook と PR TIMES RSS URL を設定  
   ※外部ライブラリ不要の簡易 .env ローダーが `config.py` にあり、`.env` があれば自動で読み込みます。
2. Python 3.10+ を用意（標準ライブラリのみ使用）

### 環境変数
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook の URL
- `PRTIMES_RSS_URLS`: 取得する RSS URL をカンマ区切りで指定（デフォルト: `https://prtimes.jp/index.rdf`）

## 使い方

### 前提
- Python 3.10+（標準ライブラリのみ利用）
- Slack Incoming Webhook URL を取得済み
- PR TIMES の RSS URL を把握していること（環境変数で指定）

### 環境変数
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook の URL
- `PRTIMES_RSS_URLS`: 取得する RSS URL をカンマ区切りで指定（例: `https://example.com/med.rss,https://example.com/it.rss`）

### 実行コマンド
```bash
# Slack送信なしの確認
python main.py --dry-run --verbose

# 通常実行
python main.py

# ローカルのサンプルRSSで動作確認（network不要）
PRTIMES_RSS_URLS=file://$(pwd)/sample_feed.xml python main.py --dry-run --verbose
```

オプション:
- `--storage-path PATH`: 配信済みURLを保存するJSONのパス（デフォルト: `data/sent_urls.json`）
- `--max-items N`: 1回の投稿に含める最大件数（デフォルト: 20）
- `--dry-run`: Slack送信せず標準出力にメッセージを表示
- `--verbose`: 詳細ログを出力

### 定期実行（例: cron）
```
0 9,15,21 * * * /usr/bin/python3 /path/to/main.py >> /var/log/prtimes_med_it.log 2>&1
```

### ディレクトリ構成（主要ファイル）
- `main.py`: 実行エントリーポイント
- `config.py`: RSS/キーワード/Slack設定
- `fetcher.py`: RSS取得
- `filter.py`: キーワードフィルタリング
- `notifier.py`: Slack投稿
- `storage.py`: 配信済みURL管理
- `data/sent_urls.json`: 配信済みURLの保存先（自動生成）
