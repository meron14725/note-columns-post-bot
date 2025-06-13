# Scripts Directory

このディレクトリには、開発・テスト・デバッグ用のスクリプトが含まれています。

## テスト・デバッグスクリプト

### test_scraper.py
Note.comスクレイパーの動作テスト用スクリプト

使用方法:
```bash
# 記事リスト収集テスト
python scripts/test_scraper.py --test list

# 記事詳細取得テスト  
python scripts/test_scraper.py --test detail

# 完全処理フローテスト
python scripts/test_scraper.py --test full
```

### debug_article_detail.py
記事詳細取得機能のデバッグ用スクリプト

使用方法:
```bash
python scripts/debug_article_detail.py
```

### debug_token.py
Note.comのセッショントークン取得のデバッグ用スクリプト

使用方法:
```bash
python scripts/debug_token.py
```

### test_api_without_token.py
XSRF-TOKEN無しでのAPI動作確認用スクリプト

使用方法:
```bash
python scripts/test_api_without_token.py
```

## 注意事項

- すべてのスクリプトはプロジェクトルートから実行してください
- スクリプト実行前に必要な依存関係がインストールされていることを確認してください
- これらのスクリプトは開発・デバッグ用であり、本番環境では使用しないでください