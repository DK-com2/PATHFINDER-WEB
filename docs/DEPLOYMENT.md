# デプロイメントガイド

## 本番環境

**運用中サイト**: https://pathfinder.dk-core.com

## Docker デプロイメント

### 基本デプロイ

```bash
# イメージビルド
docker build -t pathfinder-web .

# 環境変数ファイル準備
cp .env.example .env
# .env ファイルを実際の値で編集

# コンテナ起動
docker run -d \
  --name pathfinder-web \
  -p 8000:8000 \
  --env-file .env \
  pathfinder-web
```

### 本番環境要件

- **メモリ**: 1GB以上推奨
- **CPU**: 1コア以上
- **ストレージ**: 10GB以上（ログ・キャッシュ含む）
- **ネットワーク**: PostgreSQL・Supabaseへの接続

### 環境変数設定

本番環境では以下の環境変数を適切に設定：

```env
# データベース
DATABASE_URL=postgresql://user:password@host:port/database

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-production-anon-key

# JWT
SECRET_KEY=your-strong-production-secret-key

# 開発者ツール
DEVELOPER_PASSWORD=your-secure-production-password

# 環境
ENVIRONMENT=production
```

## セキュリティ考慮事項

1. **環境変数の保護**: 本番環境では機密情報を環境変数で管理
2. **HTTPS強制**: リバースプロキシでHTTPS化
3. **ファイアウォール**: 必要なポートのみ開放
4. **定期バックアップ**: PostgreSQLデータベースの自動バックアップ

## 監視・メンテナンス

- **ログ監視**: コンテナログの定期確認
- **リソース監視**: メモリ・CPU使用量の監視
- **データベース監視**: 接続数・クエリパフォーマンス
- **アップデート**: セキュリティアップデートの適用