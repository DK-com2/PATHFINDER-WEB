# API リファレンス

## 認証

すべてのAPIエンドポイントは、認証が必要なものについて`Authorization: Bearer <token>`ヘッダーが必要です。

## 認証API

### POST /api/auth/login
ユーザーログイン

**リクエスト:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**レスポンス:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### POST /api/auth/signup
新規アカウント作成

**リクエスト:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**レスポンス:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### POST /api/auth/logout
ログアウト（認証必要）

**レスポンス:**
```json
{
  "message": "Successfully logged out"
}
```

### GET /api/auth/verify
トークン検証（認証必要）

**レスポンス:**
```json
{
  "valid": true,
  "user": {
    "user_id": "user-uuid",
    "email": "user@example.com"
  }
}
```

### POST /api/auth/set-username
ユーザー名設定（認証必要）

**リクエスト:**
```json
{
  "username": "myusername"
}
```

**レスポンス:**
```json
{
  "message": "Username set successfully",
  "username": "myusername"
}
```

## データ管理API

### POST /api/timeline/upload
Google Timelineデータアップロード（認証必要）

**リクエスト:** multipart/form-data
- `file`: JSONファイル

**レスポンス:**
```json
{
  "message": "Upload completed successfully",
  "processed_records": 15420,
  "processing_time": 2.34
}
```

### DELETE /api/timeline/clear-data
ユーザーデータ削除（認証必要）

**レスポンス:**
```json
{
  "message": "User data cleared successfully",
  "deleted_records": 15420
}
```

### GET /api/timeline/data
地図表示用データ取得（認証必要）

**クエリパラメータ:**
- `limit`: 最大レコード数（デフォルト: 50000）

**レスポンス:**
```json
{
  "data": [
    {
      "lat": 35.6762,
      "lng": 139.6503,
      "type": "timelinePath",
      "timestamp": "2024-01-01T12:00:00Z",
      "semantic": "渋谷駅",
      "activity": "WALKING"
    }
  ],
  "total_count": 157946,
  "displayed_count": 50000
}
```

## 開発者ツールAPI

### GET /api/developer/export-all-geojson
全データGeoJSONエクスポート（パスワード認証）

**クエリパラメータ:**
- `password`: 開発者パスワード

**レスポンス:** GeoJSONファイル

### GET /api/developer/export-optimized-geojson
最適化GeoJSONエクスポート（パスワード認証）

**クエリパラメータ:**
- `password`: 開発者パスワード
- `limit`: 最大レコード数
- `days`: 過去N日のデータ
- `sample_rate`: サンプリング率（0.1-1.0）

**レスポンス:** 最適化されたGeoJSONファイル

### GET /api/developer/database-stats
データベース統計情報（パスワード認証）

**クエリパラメータ:**
- `password`: 開発者パスワード

**レスポンス:**
```json
{
  "database_stats": {
    "total_records": 157946,
    "valid_coordinates": 155230,
    "invalid_coordinates": 2716,
    "user_stats": {
      "user1": 78923,
      "user2": 79023
    },
    "type_stats": {
      "timelinePath": 98234,
      "visit": 45612,
      "activity": 14100
    }
  }
}
```

## エラーレスポンス

全APIで共通のエラーフォーマット：

```json
{
  "detail": "エラーメッセージ"
}
```

**HTTPステータスコード:**
- `400`: Bad Request（不正なリクエスト）
- `401`: Unauthorized（認証エラー）
- `403`: Forbidden（権限エラー）
- `500`: Internal Server Error（サーバーエラー）