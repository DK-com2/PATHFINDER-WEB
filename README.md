# Pathfinder Web

Google Timelineデータを可視化・管理するWebアプリケーション。FastAPI + Deck.gl によるモダンな地図表示と高速データ処理を実現。

## 主要機能

- **認証システム**: Supabase認証とJWTトークンによるセキュアなユーザー管理
- **インタラクティブマップ**: Deck.gl WebGL レンダリングによる高性能地図表示
- **データ管理**: Google Timelineデータのアップロード・削除・可視化
- **高速処理**: PostgreSQL COPYによる大量データの高速インサート
- **開発者ツール**: GeoJSONエクスポートとデータ分析API

## プロジェクト構成

```
pathfinder-web/
├── main.py                    # FastAPI メインアプリ
├── static/                    # フロントエンド
│   ├── index.html            # ダッシュボード（SPA）
│   ├── upload.html           # Google Timelineアップロード
│   ├── map.html              # Deck.gl インタラクティブマップ
│   └── app.js                # メインJavaScriptロジック
├── api/                      # バックエンドAPI
│   ├── auth.py               # Supabase認証
│   ├── database.py           # データ取得API
│   ├── timeline/             # Timeline関連
│   │   └── upload.py         # データアップロード・削除
│   └── developer/            # 開発者ツール
│       ├── routes.py         # 基本エクスポート
│       ├── simple_export.py  # シンプルGeoJSONエクスポート
│       └── optimized_routes.py # 最適化エクスポート
├── utils/                    # ユーティリティ
│   ├── database.py           # PostgreSQL接続
│   └── auth.py               # JWT認証ヘルパー
└── models/                   # データモデル
    └── user.py               # ユーザーモデル
```

## セットアップ

### 1. 環境準備

```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化
# Windows
venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env.example`を参考に`.env`ファイルを作成：

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/database

# Supabase Configuration
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-anon-key-here

# JWT Configuration
SECRET_KEY=your-secret-key-for-jwt-signing-make-it-long-and-secure

# Developer Tools
DEVELOPER_PASSWORD=your-secure-developer-password

# Environment
ENVIRONMENT=development
```

### 3. データベース構造

PostgreSQLに以下のテーブルが必要です：

```sql
-- タイムラインデータテーブル
CREATE TABLE timeline_data(
    id SERIAL NOT NULL,
    "type" varchar(255) NOT NULL,
    start_time timestamp with time zone,
    end_time timestamp with time zone,
    point_time timestamp with time zone,
    latitude double precision,
    longitude double precision,
    visit_probability double precision,
    visit_placeid varchar(255),
    visit_semantictype varchar(255),
    activity_distancemeters double precision,
    activity_type varchar(255),
    activity_probability double precision,
    username varchar(255) NOT NULL,
    _gpx_data_source varchar(50),
    _gpx_track_name varchar(255),
    _gpx_elevation double precision,
    _gpx_speed double precision,
    _gpx_point_sequence integer,
    PRIMARY KEY(id)
);

-- インデックス
CREATE INDEX timeline_data_username_idx ON public.timeline_data USING btree (username);
CREATE INDEX timeline_data_username_start_time_idx ON public.timeline_data USING btree (username, start_time DESC);
```

Supabaseには以下のテーブルが必要です：

```sql
-- ユーザー名テーブル
CREATE TABLE username (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    username VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4. サーバー起動

```bash
# 開発サーバー起動
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 使用方法

1. **アクセス**: http://localhost:8000
2. **ログイン**: Supabaseアカウントでサインイン
3. **ユーザー名設定**: 初回ログイン時に設定
4. **データアップロード**: 
   - 「Timeline アップロード」からGoogle Takeoutデータをアップロード
   - JSONファイルを選択して一括インポート
5. **マップ表示**: 
   - 「マップを見る」でインタラクティブ地図を表示
   - ズームレベルに応じた最適化表示
   - 複数の地図タイル選択可能

## API エンドポイント

### 認証
- `POST /api/auth/login` - ログイン
- `POST /api/auth/logout` - ログアウト
- `GET /api/auth/verify` - トークン検証
- `POST /api/auth/set-username` - ユーザー名設定

### データ管理
- `POST /api/timeline/upload` - Google Timelineデータアップロード
- `DELETE /api/timeline/clear-data` - ユーザーデータ削除
- `GET /api/timeline/data` - 地図表示用データ取得

### 開発者ツール
- `GET /api/developer/export-all-geojson` - 全データGeoJSONエクスポート
- `GET /api/developer/export-optimized-geojson` - 最適化エクスポート
- `GET /api/developer/database-stats` - データベース統計

## 技術スタック

**バックエンド**
- FastAPI - 高性能Python Webフレームワーク
- PostgreSQL - メインデータベース
- Supabase - 認証・ユーザー管理
- JWT - セキュアなトークン認証

**フロントエンド** 
- Deck.gl - WebGL地図可視化ライブラリ
- Vanilla JavaScript - 軽量フロントエンド
- Tailwind CSS - ユーティリティファーストCSS

**データ処理**
- PostgreSQL COPY - 高速バルクインサート
- GeoJSON - 地理データ標準フォーマット

## パフォーマンス特徴

- **大容量データ対応**: 10万件以上のTimelineポイントを快適表示
- **ズーム最適化**: レベル別データフィルタリング（≤8: 50%表示 → ≥14: 100%表示）
- **WebGL レンダリング**: GPU活用による滑らかなマップ操作
- **高速インポート**: PostgreSQL COPYで15万レコード/秒の処理速度

## トラブルシューティング

**データベース接続エラー**
- `.env`ファイルの`DATABASE_URL`設定を確認
- PostgreSQLサーバーの起動状態を確認

**認証エラー** 
- `SUPABASE_URL`と`SUPABASE_KEY`の設定を確認
- Supabaseプロジェクトのアクセス権限を確認

**マップが重い場合**
- ブラウザのハードウェアアクセラレーションを有効化
- ズームアウト時の自動データフィルタリングが動作するか確認