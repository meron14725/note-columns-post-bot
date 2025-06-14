# プロジェクトガイドライン

    このファイルは本プロジェクトのコーディング規約及び設定を記載した「ルール」または「ルールファイル」です

## 最重要ルール - 新しいルールの追加プロセス

    ユーザーから今回限りではなく常に対応が必要だと思われる指示を受けた場合：
    1. 「これを標準のルールにしますか？」と質問する
    2. YESの回答を得た場合、CLAUDE.mdに追加ルールとして記載する
    3. 以降は標準ルールとして常に適用する
    4. 要件定義、設計に関しても同じフローで追加要件or修正として追記してください

    このプロセスにより、プロジェクトルールを継続的に改善していきます。

## Git ワークフローのルール

   コードの修正・変更時は必ず以下の手順に従う：
   1. 修正用のブランチを切る（feature/fix-xxx 形式）
   2. ブランチで修正作業を実施
   3. プルリクエストを作成
   4. ユーザーがレビュー・マージを行う
   5. mainブランチに直接コミット・プッシュは禁止

   **重要**: 
   - 全ての修正作業（バグ修正、機能追加、ドキュメント更新等）は必ず新しいブランチで行う
   - ブランチ名は作業内容を表す分かりやすい名前にする（例：feature/add-xxx, fix/resolve-xxx）
   - 作業完了後は必ずプルリクエストを作成し、ユーザーの承認を得てからマージする

## プルリクエスト記載ルール

   プルリクエストのタイトル・説明は必ず日本語で記載する：
   - タイトル：「機能: 〇〇を追加」「修正: 〇〇の不具合を解決」形式
   - 説明文：日本語でわかりやすく記載
   - 変更内容・目的・影響範囲を明記
   - 英語での記載は禁止

1. パッケージ管理

   - `uv` のみを使用し、`pip` は絶対に使わない
   - インストール方法：`uv add package`
   - ツールの実行：`uv run tool`
   - アップグレード：`uv add --dev package --upgrade-package package`
   - 禁止事項：`uv pip install`、`@latest` 構文の使用

2. コード品質

   - すべてのコードに型ヒントを必須とする
   - パブリック API には必ずドキュメンテーション文字列（docstring）を付ける
   - 関数は集中して小さく保つこと
   - 既存のパターンを正確に踏襲すること
   - 行の最大長は 88 文字まで

3. テスト要件
   - テストフレームワーク：`uv run --frozen pytest`
   - 非同期テストは `asyncio` ではなく `anyio` を使用
   - カバレッジはエッジケースやエラーも含めてテストすること
   - 新機能には必ずテストを追加すること
   - バグ修正にはユニットテストを追加すること

## 要件定義

エンタメコラム自動収集・公開システム 要件定義書

1. システム概要
   note のエンタメ系カテゴリから優良なコラム記事を自動収集し、AI による評価を行った上で、GitHub Pages を利用した Web サイトへの掲載と X（Twitter）での自動投稿を行うシステム。
2. 機能要件
   2.1 記事収集機能

バッチ処理：毎日定時実行
取得元：note API を使用（カテゴリ別）
取得ロジック：

1 ページ目から順次取得
公開日が 1 日以上前の記事が出現した時点で取得停止
無料公開記事のみを対象

URL 管理：urls_config.json で管理（追加・削除が容易）

2.2 AI 評価機能

評価項目：

文章の質（構成・読みやすさ）：40 点
内容の独自性：30 点
エンタメ性の高さ：30 点

合計 100 点満点で評価

プロンプト管理：prompt_settings.json で管理
評価データ保存：評価結果を DB に保存
処理能力：

1 日 100 記事の評価が約 4 分で完了
最大 14,400 記事/日まで処理可能（無料枠内）

2.3 Web サイト機能

ホスティング：GitHub Pages（完全無料）
データ更新方式：

バッチ処理で JSON ファイル生成
GitHub リポジトリに push
GitHub Pages が自動的に更新

掲載内容：

記事タイトル
AI 生成の紹介文（200 文字程度）
アイキャッチ画像（note から取得）
元記事へのリンク
評価スコア表示

表示形式：カード型レイアウト（静的サイト）
更新頻度：毎日自動更新

2.4 X（Twitter）自動投稿機能

投稿回数：1 日 2 回
投稿内容：

「本日のエンタメコラム TOP5」
順位、記事タイトル、リンク

投稿時間：posting_schedule.json で管理

3. 非機能要件
   3.1 技術スタック

バックエンド処理：Python 3.9+
データベース：SQLite（無料運用のため）
AI：Groq Cloud（Llama 3 70B - 完全無料）

無料枠：14,400 リクエスト/日、30 リクエスト/分
高品質な日本語対応
API 経由で完全自動化可能

フロントエンド：

静的サイト（HTML/CSS/JavaScript）
GitHub Pages でホスティング

定期実行：GitHub Actions（無料枠内）
データ連携：JSON ファイル経由

3.2 設定ファイル構成
config/
├── urls_config.json # 収集対象 URL 一覧
├── prompt_settings.json # AI 評価プロンプト
├── posting_schedule.json # X 投稿スケジュール
└── api_keys.json # 各種 API キー（Groq API キー含む）
3.3 コスト

完全無料で運用可能

Groq Cloud: 無料（1 日 100 記事なら余裕）
GitHub Actions: プライベートリポジトリでも無料枠内
GitHub Pages: 無料
独自ドメイン: オプション（年間約 1,000 円）

4. データ構造
   4.1 記事データ（DB）
   python{
   "id": "note 記事 ID",
   "title": "記事タイトル",
   "url": "記事 URL",
   "thumbnail": "アイキャッチ画像 URL",
   "published_at": "公開日時",
   "author": "著者名",
   "content_preview": "記事冒頭テキスト",
   "ai_score": {
   "quality": 40,
   "originality": 30,
   "entertainment": 30,
   "total": 100
   },
   "ai_summary": "AI 生成の紹介文",
   "evaluated_at": "評価日時"
   }
   4.2 JSON 出力形式（GitHub Pages 用）
   json{
   "lastUpdated": "2024-01-01T06:00:00+09:00",
   "articles": [
   {
   "id": "xxxxx",
   "title": "記事タイトル",
   "url": "https://note.com/...",
   "thumbnail": "https://...",
   "author": "著者名",
   "published_at": "2024-01-01T00:00:00",
   "total_score": 85,
   "scores": {
   "quality": 35,
   "originality": 25,
   "entertainment": 25
   },
   "ai_summary": "この記事は...",
   "evaluated_at": "2024-01-01T06:00:00"
   }
   ]
   }
5. 処理フロー

記事収集（毎日 AM6:00）

urls_config.json から対象 URL を読み込み
各 URL に対して API 呼び出し
新規記事のみ DB 保存

AI 評価（収集後自動実行）

未評価記事を抽出
Groq Cloud API で評価（レート制限考慮）
prompt_settings.json のプロンプトで評価
スコアと紹介文を生成・保存
100 記事なら約 4 分で完了

JSON 生成と Web サイト更新（評価後自動実行）

DB から評価済み記事を取得
JSON ファイルに変換
GitHub リポジトリの docs/data/に配置
Git commit & push
GitHub Pages が自動的に更新

X 投稿（設定時刻）

当日の TOP5 記事を抽出
投稿フォーマットに整形
X API で投稿

6. エラーハンドリング

API 制限エラー：リトライ処理（3 回まで）
評価エラー：該当記事をスキップし、ログ記録
投稿エラー：管理者に通知メール
レート制限対策：自動的に待機時間を挿入
Git push 失敗：リトライ処理

## Issue対応手順

Issue解決中に新たな問題が発生した場合：
1. 問題の原因を特定・分析
2. 修正方法を決定・実装
3. Sub Issueとしてこのファイルに記録：
   - 問題の内容
   - 原因の説明
   - 実装した修正方法
   - 影響したファイル
4. GitHubにSub Issueを作成
5. 修正完了後、動作確認を実施
6. GitHubのSub Issueを修正完了として閉じる

## 解決済みSub Issues

### Sub Issue #10: AI評価レスポンス解析エラーの修正 (2025-06-15)
- **問題**: 必須フィールド欠損と文字数超過でAI評価が失敗
- **原因**: AIレスポンスの形式不整合と検証不足
- **修正**: データ検証・フォールバック処理を追加
- **ファイル**: `backend/app/services/evaluator.py`

### Sub Issue #11: JSON生成の非同期エラーの修正 (2025-06-15)
- **問題**: 同期関数に対してawaitを適用しエラー発生
- **原因**: 非同期関数の戻り値型の不整合
- **修正**: 非同期呼び出しを同期呼び出しに修正
- **ファイル**: `backend/batch/daily_process_improved.py`

### Sub Issue #13: note記事リンク大量貼り付け記事の除外機能 (2025-06-15)
- **問題**: note記事内に他のnote記事リンクが4つ以上ある品質の悪い記事を除外する必要がある
- **要件**: AI評価前にnote.comリンクが4つ以上あったら評価対象外としてDB保存
- **実装内容**:
  - `ContentQualityChecker`クラス作成でnote.comリンク検出・除外判定
  - データベースに`is_excluded`、`exclusion_reason`列追加
  - スクレイパーでコンテンツ品質チェック機能追加
  - 日次処理で除外記事のAI評価スキップ処理追加
- **修正ファイル**:
  - `backend/app/utils/content_quality.py` (新規作成)
  - `backend/app/models/article.py` (除外フィールド追加)
  - `backend/app/repositories/article_repository.py` (除外処理追加)
  - `backend/app/services/scraper.py` (品質チェック追加)
  - `backend/batch/daily_process.py` (除外ロジック追加)
  - `backend/database/schema.sql` (除外列追加)

7. 運用・保守

ログファイル：logs/ディレクトリに日付別保存
バックアップ：

SQLite ファイルの日次バックアップ
JSON ファイルのアーカイブ保存

監視：GitHub Actions の実行結果通知
パフォーマンス：

1 日 100 記事：約 4 分で処理完了
1 日 1000 記事：約 34 分で処理完了（無料枠内）

8. 拡張性考慮

カテゴリ追加：urls_config.json に追加するだけ
評価基準変更：prompt_settings.json 編集
投稿時間変更：posting_schedule.json 編集
スケール対応：

100 記事/日：現行構成で対応
1000 記事/日：バッチ分割で対応
5000 記事/日以上：複数 API キーで対応

9. システムの利点

完全無料：すべてのサービスが無料枠内で運用可能
高品質 AI：Llama 3 70B による優れた評価精度
完全自動化：人手を介さずに運用可能
常時公開：GitHub Pages で 24 時間アクセス可能
拡張性：記事数増加にも柔軟に対応
運用容易性：設定ファイルの編集だけで各種変更が可能

## エンタメコラム自動収集・公開システム 基本設計書

1. システム構成図
   ┌─────────────────────────────────────────────────────────────┐
   │ GitHub Actions │
   │ ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ │
   │ │ Daily Batch │→ │Generate JSON │→ │ Git Push │ │
   │ │ (収集+評価) │ │ (静的ファイル) │ │(GitHub Pages)│ │
   │ └─────────────┘ └──────────────┘ └──────────────┘ │
   │ ┌─────────────┐ ┌──────────────┐ │
   │ │Tweet Post │ │ Backup Job │ │
   │ └─────────────┘ └──────────────┘ │
   └───────────────────────────────────────────────────┬─────────┘
   │
   ┌───────────────────────────────┼─────────┐
   │ ▼ │
   ┌───────────────────┼─────────┐ ┌─────────────────────────┤
   │ Backend Server │ │ │ GitHub Pages │
   │ ┌─────────────┐ │ │ │ ┌─────────────────┐ │
   │ │ Scraper │ │ │ │ │ Static Site │ │
   │ │ (note) │ │ │ │ │ (HTML/JS/CSS) │ │
   │ └──────┬──────┘ │ │ │ └────────┬────────┘ │
   │ ┌──────▼──────┐ │ │ │ │ │
   │ │ Evaluator │ │ │ │ ┌────────▼────────┐ │
   │ │(Groq Cloud) │ │ │ │ │ data/ │ │
   │ └──────┬──────┘ │ │ │ │ - articles.json │ │
   │ ┌──────▼──────┐ │ │ │ │ - top5.json │ │
   │ │JSON Generator│──┘ │ │ │ - meta.json │ │
   │ └──────┬──────┘ │ │ └─────────────────┘ │
   │ ┌──────▼──────┐ │ └─────────────────────────┘
   │ │ SQLite │ │ │
   │ │ DB │ │ ▼
   │ └─────────────┘ │ ┌──────────────────┐
   │ │ │ │ Web Browser │
   │ ▼ │ │ (End User) │
   │ ┌─────────────┐ │ └──────────────────┘
   │ │Twitter Bot │─────────────┘
   │ └─────────────┘
   └─────────────────┘
2. ディレクトリ構造（改訂版）
   entertainment-column-system/
   ├── backend/ # バックエンド処理
   │ ├── app/
   │ │ ├── **init**.py
   │ │ ├── models/ # データモデル
   │ │ │ ├── **init**.py
   │ │ │ ├── article.py # 記事モデル
   │ │ │ └── evaluation.py # 評価モデル
   │ │ ├── services/ # ビジネスロジック
   │ │ │ ├── **init**.py
   │ │ │ ├── scraper.py # note 記事収集
   │ │ │ ├── evaluator.py # AI 評価（Groq Cloud）
   │ │ │ ├── json_generator.py # JSON 生成
   │ │ │ └── twitter_bot.py # X 投稿処理
   │ │ ├── repositories/ # データアクセス層
   │ │ │ ├── **init**.py
   │ │ │ ├── article_repository.py
   │ │ │ └── evaluation_repository.py
   │ │ └── utils/ # ユーティリティ
   │ │ ├── **init**.py
   │ │ ├── database.py # DB 接続管理
   │ │ ├── logger.py # ログ設定
   │ │ └── rate_limiter.py # レート制限
   │ ├── batch/ # バッチ処理スクリプト
   │ │ ├── **init**.py
   │ │ ├── daily_process.py # 日次処理統合スクリプト
   │ │ └── post_to_twitter.py # X 投稿バッチ
   │ ├── database/ # データベース関連
   │ │ ├── schema.sql # スキーマ定義
   │ │ └── entertainment_columns.db # SQLite データベース
   │ ├── output/ # 一時出力ディレクトリ
   │ │ └── .gitkeep
   │ ├── logs/ # ログファイル
   │ │ └── .gitkeep
   │ ├── tests/ # テストコード
   │ │ ├── **init**.py
   │ │ ├── test_scraper.py
   │ │ └── test_evaluator.py
   │ └── requirements.txt # Python パッケージ
   │
   ├── docs/ # GitHub Pages 用（公開ディレクトリ）
   │ ├── index.html # メインページ
   │ ├── css/
   │ │ └── style.css # スタイルシート
   │ ├── js/
   │ │ └── main.js # フロントエンドロジック
   │ ├── data/ # JSON データ（毎日更新）
   │ │ ├── articles.json # 全記事データ
   │ │ ├── top5.json # TOP5 記事
   │ │ ├── meta.json # メタ情報
   │ │ └── archives/ # 過去データアーカイブ
   │ │ └── .gitkeep
   │ └── CNAME # 独自ドメイン設定（オプション）
   │
   ├── config/ # 設定ファイル
   │ ├── urls_config.json # 収集対象 URL
   │ ├── prompt_settings.json # AI 評価プロンプト
   │ ├── posting_schedule.json # X 投稿スケジュール
   │ └── config.py # アプリケーション設定
   │
   ├── .github/ # GitHub Actions
   │ └── workflows/
   │ ├── daily_update.yml # 日次更新（収集 → 評価 → サイト更新）
   │ ├── twitter_post.yml # X 投稿
   │ └── backup.yml # バックアップ
   │
   ├── .env.example # 環境変数サンプル
   ├── .gitignore
   └── README.md
3. データベース設計（変更なし）
   3.1 テーブル構成
   articles テーブル
   sqlCREATE TABLE articles (
   id TEXT PRIMARY KEY, -- note 記事 ID
   title TEXT NOT NULL, -- 記事タイトル
   url TEXT NOT NULL UNIQUE, -- 記事 URL
   thumbnail TEXT, -- アイキャッチ画像 URL
   published_at DATETIME NOT NULL, -- 公開日時
   author TEXT NOT NULL, -- 著者名
   content_preview TEXT, -- 記事冒頭テキスト
   category TEXT NOT NULL, -- カテゴリ
   collected_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 収集日時
   is_evaluated BOOLEAN DEFAULT FALSE, -- 評価済みフラグ
   created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
   updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
   );

CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_is_evaluated ON articles(is_evaluated);
evaluations テーブル
sqlCREATE TABLE evaluations (
id INTEGER PRIMARY KEY AUTOINCREMENT,
article_id TEXT NOT NULL, -- 記事 ID（外部キー）
quality_score INTEGER NOT NULL, -- 文章の質スコア（0-40）
originality_score INTEGER NOT NULL, -- 独自性スコア（0-30）
entertainment_score INTEGER NOT NULL, -- エンタメ性スコア（0-30）
total_score INTEGER NOT NULL, -- 合計スコア（0-100）
ai_summary TEXT NOT NULL, -- AI 生成の紹介文
evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE INDEX idx_evaluations_total_score ON evaluations(total_score DESC);
CREATE INDEX idx_evaluations_evaluated_at ON evaluations(evaluated_at);
twitter_posts テーブル
sqlCREATE TABLE twitter_posts (
id INTEGER PRIMARY KEY AUTOINCREMENT,
tweet_id TEXT, -- X(Twitter)の投稿 ID
content TEXT NOT NULL, -- 投稿内容
posted_at DATETIME, -- 投稿日時
status TEXT DEFAULT 'pending', -- pending/posted/failed
error_message TEXT, -- エラーメッセージ
created_at DATETIME DEFAULT CURRENT_TIMESTAMP
); 4. 主要処理フロー
4.1 日次バッチ処理フロー
python# backend/batch/daily_process.py
class DailyBatchProcessor:
"""日次バッチ処理の統合クラス"""

    def run(self):
        # 1. スクレイピング
        articles = self.scraper.collect_articles()

        # 2. DB保存
        self.repository.save_articles(articles)

        # 3. AI評価
        unevaluated = self.repository.get_unevaluated_articles()
        evaluations = self.evaluator.evaluate_batch(unevaluated)

        # 4. 評価結果保存
        self.repository.save_evaluations(evaluations)

        # 5. JSON生成
        self.generate_json_files()

        # 6. 出力完了
        return True

    def generate_json_files(self):
        """GitHub Pages用のJSONファイル生成"""
        # DBから最新データ取得
        articles = self.repository.get_today_evaluated_articles()

        # JSON形式に変換
        json_data = self.format_for_web(articles)

        # ファイル出力
        self.save_json_files(json_data)

4.2 GitHub Actions ワークフロー
yaml# .github/workflows/daily_update.yml
name: Daily Update Website

on:
schedule: - cron: '0 21 \* \* \*' # JST 6:00 AM
workflow_dispatch:

jobs:
update-website:
runs-on: ubuntu-latest
steps: # 1. リポジトリチェックアウト - uses: actions/checkout@v3

      # 2. Python環境構築
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      # 3. 依存関係インストール
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      # 4. バッチ処理実行
      - name: Run daily batch
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
        run: |
          cd backend
          python batch/daily_process.py

      # 5. JSONファイルをdocsにコピー
      - name: Update website data
        run: |
          cp backend/output/articles.json docs/data/
          cp backend/output/top5.json docs/data/
          echo "{\"lastUpdated\": \"$(date -Iseconds)\"}" > docs/data/meta.json

          # アーカイブ保存
          mkdir -p docs/data/archives
          cp backend/output/articles.json "docs/data/archives/$(date +%Y%m%d).json"

      # 6. Git commit & push
      - name: Commit and push
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git add docs/data/
          git commit -m "🔄 Update articles - $(date +'%Y/%m/%d')"
          git push

5. セキュリティ設計
   5.1 API キー管理

GitHub Secrets 使用
環境変数経由でアクセス
ローカル開発は.env ファイル

5.2 データ保護

SQLite ファイルは backend 内に保持
公開用 JSON のみ docs に配置
個人情報は含めない

5.3 アクセス制御

GitHub Pages は読み取り専用
更新は GitHub Actions 経由のみ

6. 運用想定
   6.1 日次運用フロー

AM 6:00 - バッチ処理開始
AM 6:04 - 評価完了、JSON 生成
AM 6:05 - GitHub Pages 更新完了
AM 10:00 - 1 回目の X 投稿
PM 7:00 - 2 回目の X 投稿

6.2 監視項目

GitHub Actions 実行状況
エラーログ
記事収集数・評価数
