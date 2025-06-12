# AI厳選エンタメコラム

AIが厳選したnoteのエンタメコラムを自動収集・評価し、GitHub Pagesで公開するシステムです。

## 🌟 特徴

- 📰 **自動記事収集**: noteのエンタメカテゴリから新着記事を自動収集
- 🤖 **AI評価**: Groq Cloud (Llama 3 70B) による高精度な記事評価
- 📊 **スコアリング**: 文章の質・独自性・エンタメ性を100点満点で評価
- 🌐 **Web公開**: GitHub Pagesによる無料ホスティング
- 🐦 **SNS連携**: X(Twitter)への自動投稿
- 🔄 **完全自動化**: GitHub Actionsによる毎日の自動運用

## 📋 評価基準

- **文章の質** (40点): 構成・読みやすさ・論理性
- **内容の独自性** (30点): 新しい視点・情報の独自性
- **エンタメ性** (30点): 面白さ・読者を引き込む魅力

## 🛠️ 技術スタック

### バックエンド
- **Python 3.9+** - メイン開発言語
- **uv** - 高速パッケージ管理
- **SQLite** - データベース
- **Groq Cloud** - AI評価エンジン
- **httpx/BeautifulSoup** - Web スクレイピング
- **Tweepy** - Twitter API

### フロントエンド
- **HTML/CSS/JavaScript** - 静的ウェブサイト
- **GitHub Pages** - ホスティング

### インフラ
- **GitHub Actions** - CI/CD・自動化
- **GitHub Secrets** - 認証情報管理

## 🚀 セットアップ

### 1. 環境構築

```bash
# リポジトリのクローン
git clone <repository-url>
cd note-columns-post-bot

# uvのインストール (まだの場合)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存関係のインストール
uv sync
```

### 2. 環境変数の設定

`.env`ファイルを作成し、必要なAPIキーを設定:

```bash
# .env
GROQ_API_KEY=your_groq_api_key_here
TWITTER_API_KEY=your_twitter_api_key_here
TWITTER_API_SECRET=your_twitter_api_secret_here
TWITTER_ACCESS_TOKEN=your_twitter_access_token_here
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret_here
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
```

### 3. データベースの初期化

```bash
# データベースの作成（初回のみ）
uv run python -c "
from backend.app.utils.database import db_manager
db_manager.init_database()
print('Database initialized successfully')
"
```

### 4. 設定ファイルの調整

必要に応じて `config/` ディレクトリ内の設定ファイルを調整:

- `urls_config.json` - 収集対象URL
- `prompt_settings.json` - AI評価プロンプト
- `posting_schedule.json` - 投稿スケジュール

## 💻 使用方法

### 手動実行

```bash
# 記事収集と評価の実行
uv run python backend/batch/daily_process.py

# Twitter投稿の実行
uv run python backend/batch/post_to_twitter.py
```

### 自動実行

GitHub Actionsにより以下のスケジュールで自動実行:

- **記事収集・評価**: 毎日 6:00 JST
- **Twitter投稿**: 毎日 10:00, 19:00 JST
- **バックアップ**: 毎週日曜 9:00 JST

## 🔧 GitHub Actions設定

### 必要なSecrets

GitHub リポジトリの Settings > Secrets and variables > Actions で設定:

```
GROQ_API_KEY=your_groq_api_key
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
```

### Variables

```
GITHUB_PAGES_URL=https://username.github.io/repository-name
```

### GitHub Pages設定

1. Settings > Pages
2. Source: Deploy from a branch
3. Branch: main / docs

## 📁 プロジェクト構造

```
entertainment-column-system/
├── backend/                 # バックエンド処理
│   ├── app/
│   │   ├── models/         # データモデル
│   │   ├── services/       # ビジネスロジック
│   │   ├── repositories/   # データアクセス
│   │   └── utils/          # ユーティリティ
│   ├── batch/              # バッチ処理
│   └── database/           # データベース
├── docs/                   # GitHub Pages用
│   ├── css/
│   ├── js/
│   └── data/              # JSON データ
├── config/                 # 設定ファイル
├── .github/workflows/      # GitHub Actions
└── README.md
```

## 🧪 テスト

```bash
# テストの実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=backend

# 型チェック
uv run mypy backend/

# リンター
uv run ruff check backend/
uv run black --check backend/
```

## 📊 監視とログ

- **ログ**: `backend/logs/` ディレクトリに保存
- **GitHub Actions**: 実行ログとアーティファクト
- **データベース**: 統計情報とエラーログ

## 🔄 運用フロー

1. **記事収集** (毎日 6:00 JST)
   - noteから新着記事を収集
   - データベースに保存

2. **AI評価** (収集後自動実行)
   - 未評価記事をAIで評価
   - スコアと要約を生成

3. **JSON生成** (評価後自動実行)
   - WebサイトデータのJSONファイル生成
   - GitHub Pagesへの配置

4. **SNS投稿** (毎日 10:00, 19:00 JST)
   - TOP5記事をTwitterに投稿

## 📈 コスト

- **完全無料運用** が可能
- Groq Cloud: 無料枠内で運用
- GitHub Actions: 無料枠内で運用
- GitHub Pages: 無料

## 🤝 コントリビューション

1. Fork this repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 ライセンス

This project is licensed under the MIT License.

## 🙏 謝辞

- [Groq Cloud](https://groq.com/) - AI評価エンジン
- [note](https://note.com/) - 記事提供プラットフォーム
- [GitHub](https://github.com/) - ホスティング・CI/CD

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>