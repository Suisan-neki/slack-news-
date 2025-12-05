# 医療×ITニュース自動配信システム

医療×IT領域のニュースを複数のソースから取得し、Slack に1日3回（9時、15時、21時）まとめて投稿するためのツールです。

## 機能概要

- **複数ソースからの記事取得**
  - PR TIMES（RSSフィード）
  - 医療テックニュース（Webスクレイピング）
  - ヘルステックウォッチ（Webスクレイピング）
  - Google News（RSSフィード）

- **記事のフィルタリング**
  - タイトル/概要に「医療系キーワード」かつ「IT系キーワード」を含む記事のみ抽出
  - 除外キーワードに該当する記事は除外（美容整形、食品関連、EC関連など）

- **記事の概要（description）取得**
  - 各ソースから記事ページにアクセスして適切なdescriptionを取得
  - meta description、og:description、または記事本文から抽出

- **重複除去**
  - URLとタイトルベースで重複を除去
  - PR TIMESを最優先として、優先度の高いソースの記事を残す

- **過去送信済みURL管理**
  - JSONで送信済みURLを保持し、重複送信を防止
  - 同じ日の別時間帯でも重複を防ぐ

- **Slack投稿**
  - 抽出記事をソース別にグループ化して1つのメッセージにまとめて投稿
  - 件数が多い場合は上限（デフォルト20件）までに制限
  - 記事がない場合は「新着なし」を送信

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/Suisan-neki/slack-news-.git
cd slack-news-
```

### 2. 環境変数の設定

`.env` ファイルを作成し、以下の環境変数を設定します：

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
EXTRA_SOURCES=medicaltech,htwatch,googlenews
LOG_FILE=/path/to/cron.log
```

**環境変数の説明：**
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook の URL（必須）
- `PRTIMES_RSS_URLS`: PR TIMESのRSS URLをカンマ区切りで指定（デフォルト: `https://prtimes.jp/index.rdf`）
- `EXTRA_SOURCES`: 追加サイトをスクレイピングする場合に指定（カンマ区切り）
  - `medicaltech`: 医療テックニュース
  - `htwatch`: ヘルステックウォッチ
  - `googlenews` または `google-news`: Google News（デフォルトでは除外）
- `LOG_FILE`: ログをファイルに出力したい場合のパス（オプション）
- `EXCLUDE_EXTRA_KEYWORDS`: 除外キーワードをカンマ区切りで追加する（例: `求人,採用,転職`）
- `EXCLUDE_DOMAINS`: 除外したいドメインをカンマ区切りで指定する（例: `example.com,foo.jp`）
- `TIME_RANGE_HOURS`: 取得対象とする時間範囲（時間）。デフォルトは直近6時間（1コマ）を集計して送信します。

### 3. Python環境

- Python 3.9+ が必要（標準ライブラリのみ使用、外部依存なし）

## 使い方

### 手動実行（テスト用）

```bash
# Slack送信なしの確認（dry-run）
python3 main.py --dry-run --verbose

# 手動実行モード（送信済みURLチェックをスキップ、5件に制限、Google News除外）
python3 main.py --manual --verbose

# 通常実行（実際にSlackに送信）
python3 main.py
```

**コマンドラインオプション：**
- `--dry-run`: Slack送信せず標準出力にメッセージを表示
- `--manual`: 手動実行モード（送信済みURLチェックをスキップ、5件に制限、Google News除外）
- `--verbose`: 詳細ログを出力
- `--storage-path PATH`: 配信済みURLを保存するJSONのパス（デフォルト: `data/sent_urls.json`）
- `--max-items N`: 1回の投稿に含める最大件数（デフォルト: 20）

## 定時実行と重複防止

### 定時実行を有効にする（macOS LaunchAgent想定）

コードを更新した後は、LaunchAgentを再ロードして最新コードを使うようにします：

```bash
launchctl unload ~/Library/LaunchAgents/com.suisan.slack-news-09.plist
launchctl unload ~/Library/LaunchAgents/com.suisan.slack-news-15.plist
launchctl unload ~/Library/LaunchAgents/com.suisan.slack-news-21.plist
launchctl load ~/Library/LaunchAgents/com.suisan.slack-news-09.plist
launchctl load ~/Library/LaunchAgents/com.suisan.slack-news-15.plist
launchctl load ~/Library/LaunchAgents/com.suisan.slack-news-21.plist
```

### 手動送信と定時送信の違い

#### 手動送信（本番と分けて実行）

```bash
python3 main.py --manual --verbose
```

- Google Newsを除外
- 5件に制限
- 送信済みチェックをスキップ
- 送信したURLは `data/sent_urls.json` に記録される
- その後の定時実行では同じ記事を再送しない

#### 定時送信

```bash
python3 main.py
```

- 直近24時間分から未送信のものだけ送信
- 手動で送ったものも含め、`data/sent_urls.json` にあるURLは再送されない
- 同じ日の別時間帯でも重複を防ぐ

### 確認ポイント

1. **`data/sent_urls.json` が消えないように確認**
   - パスと権限が正しく設定されているか確認
   - ファイルが存在し、書き込み可能であることを確認

2. **環境変数の確認**
   - `SLACK_WEBHOOK_URL` 環境変数が設定されているか確認

3. **ログの確認**
   - `cron.log` または `LOG_FILE` で以下のログを確認：
     - `Loaded X sent URLs` - 送信済みURLの読み込み数
     - `New articles: Y` - 新規記事数
   - これらのログで重複抑止の動作が確認できます

この状態で、手動配信済みの記事は次の定時配信から除外され、定時配信内でも同じ時間帯で重複は出ません。

## ディレクトリ構成

```
slack-news-/
├── main.py              # 実行エントリーポイント
├── config.py            # 設定（RSS/キーワード/Slack）
├── fetcher.py           # RSSフィード取得と記事ページからのdescription取得
├── filter.py            # キーワードフィルタリング
├── notifier.py          # Slack投稿
├── storage.py           # 配信済みURL管理
├── extrasources.py      # 追加ソース（医療テックニュース、ヘルステックウォッチ、Google News）
├── data/
│   └── sent_urls.json   # 配信済みURLの保存先（自動生成）
└── README.md            # このファイル
```

## キーワード設定

### 医療系キーワード

`config.py` の `MEDICAL_KEYWORDS` で定義されています。例：
- 医療、ヘルスケア、診療、病院、クリニック
- 介護、介護施設、薬局、医師
- 医療DX、デジタルヘルス、遠隔医療、オンライン診療
- など

### IT系キーワード

`config.py` の `IT_KEYWORDS` で定義されています。例：
- AI、IT、DX、デジタル、システム
- クラウド、SaaS、アプリ、IoT
- データ、分析、解析、プラットフォーム
- など

### 除外キーワード

`config.py` の `EXCLUDE_KEYWORDS` で定義されています。以下のような記事は除外されます：
- 美容整形、エステ、化粧品、フィットネス
- 健康食品、レストラン、グルメ
- 不動産、マンション、投資
- EC、クラウドファンディング、ゲーム
- など

## 動作の流れ

1. **記事取得**
   - RSSフィードから記事を取得（PR TIMES、Google News）
   - Webスクレイピングで記事を取得（医療テックニュース、ヘルステックウォッチ）

2. **description取得**
   - 各記事のページにアクセスしてdescriptionを取得
   - meta description、og:description、または記事本文から抽出

3. **フィルタリング**
   - 医療系キーワードとIT系キーワードの両方を含む記事のみ抽出
   - 除外キーワードに該当する記事を除外

4. **重複除去**
   - URLとタイトルベースで重複を除去
   - 優先度の高いソースの記事を残す

5. **送信済みチェック**
   - 過去に送信したURLをチェック
   - 未送信の記事のみを抽出

6. **Slack投稿**
   - ソース別にグループ化してメッセージを作成
   - Slack Incoming Webhook に投稿

## トラブルシューティング

### ログの確認

```bash
# ログファイルを確認
tail -f cron.log

# エラーのみ確認
grep ERROR cron.log
```

### 手動実行でテスト

```bash
# dry-runモードで動作確認
python3 main.py --dry-run --verbose

# 手動実行モードで実際にSlackに送信（5件に制限）
python3 main.py --manual --verbose
```


## ライセンス

このプロジェクトのライセンス情報はリポジトリを確認してください。

## 更新履歴

- 2025-11-28: 全媒体でdescription取得機能を実装、除外キーワードを大幅に追加
- 複数ソース対応（医療テックニュース、ヘルステックウォッチ、Google News）
- RSS 1.0 (RDF)形式に対応
- 重複除去機能の改善
