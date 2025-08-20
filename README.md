# Pathfinder Web

**デモサイト**: https://pathfinder.dk-core.com

## プロジェクト概要

Google Timeline や GPX など異なる形式の移動記録を**統一フォーマットで保管・可視化**するための基盤として構築されたWebアプリケーション。FastAPI + Deck.gl による地図表示と大量データ処理を実現しています。

## 将来展望

**Google Mapに頼らない、自分だけのライフログを作りたい**  
Google Mapの位置履歴って便利だけど、なんだか「借り物」な感じがしませんか？データはGoogleのもので、いつサービスが変わるかもわからない。だから、自分の移動記録は自分でコントロールできるシステムを作りたいと思ってこのプロジェクトを始めました。

**次にやりたいこと: スマホから自動で位置を集める仕組み**  
今は[Push Notification API](https://github.com/DK-com2/Push-Notification-API)というシステムを開発中で、スマートフォンアプリから自動で位置情報を収集するシステムを検討中です。Google Takeoutみたいに「データをダウンロードして...」なんて面倒なことをしなくても、リアルタイムで自分の行動を記録できるようにしたいです。

**最終的に実現したいこと: あなた専用の地図サービス**  
自分の足跡で作る、自分だけの地図。それがこのプロジェクトの最終目標です。

## デモアクセス

**今すぐ試せます**: https://pathfinder.dk-core.com

![Pathfinder Web デモ画面（2015~2025までの軌跡）](docs/images/demo.png)

- **デモログイン**: 「デモアカウントでログイン」ボタンをクリック
- **新規登録**: メールアドレスで無料アカウント作成
- **モバイル対応**: スマートフォン・タブレットからもアクセス可能

## 主要機能

**認証・ユーザー管理**
- Supabase認証とJWTトークンによるセキュアなログイン
- 新規アカウント作成機能
- デモアカウントでの即座体験

**地図可視化**
- Deck.gl WebGLによる高性能な地図表示
- 15万件以上のデータポイントを軽快に表示
- ズームレベル別の自動データ最適化
- 複数マップスタイル（OpenStreetMap、白基調、衛星画像）
- モバイル対応・折りたたみ可能な情報パネル

**データ管理** 
- Google Timelineデータの高速アップロード（JSON形式）
- ユーザー別データ削除・管理機能
- PostgreSQL COPYによる大量データ高速処理

**開発者ツール**
- GeoJSONエクスポート機能
- データベース統計・分析API
- 最適化されたデータエクスポート

## システム構成

![システム構成図](docs/images/system-architecture.svg)

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
├── models/                   # データモデル
│   └── user.py               # ユーザーモデル
├── docs/                     # ドキュメント
│   ├── images/               # 図・画像ファイル
│   ├── API.md                # APIリファレンス
│   ├── DEPLOYMENT.md         # デプロイメントガイド
│   └── MEMORY_OPTIMIZATION.md # メモリ最適化計画
└── Dockerfile                # Docker設定
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

### オンラインデモ（推奨）
1. **デモサイトアクセス**: https://pathfinder.dk-core.com
2. **デモログイン**: 「デモアカウントでログイン」で即座体験
3. **新規アカウント**: 本格利用時はメールアドレスで登録

### 基本的な使い方
1. **ログイン**: デモアカウントまたは作成したアカウントでサインイン
2. **ユーザー名設定**: 初回ログイン時に任意のユーザー名を設定
3. **データアップロード**: 
   - 「Timeline アップロード」からGoogle Takeoutデータをアップロード
   - Google TakeoutでエクスポートしたJSONファイルを一括インポート
4. **地図表示**: 
   - 「地図で表示」でインタラクティブ地図を表示
   - ズームで詳細度自動調整、スマートフォンでは情報パネル折りたたみ可能
   - OpenStreetMap・白基調・衛星画像から地図スタイル選択

### ローカル開発環境
開発者向けのローカル実行方法は本ドキュメント後半の「セットアップ」を参照してください。

## API エンドポイント

### 認証API
- `POST /api/auth/login` - ログイン認証
- `POST /api/auth/signup` - 新規アカウント作成
- `POST /api/auth/logout` - ログアウト
- `GET /api/auth/verify` - JWTトークン検証
- `POST /api/auth/set-username` - ユーザー名設定

### データ管理API
- `POST /api/timeline/upload` - Google TimelineデータJSONアップロード
- `DELETE /api/timeline/clear-data` - ユーザーデータ一括削除
- `GET /api/timeline/data` - 地図表示用データ取得（ズーム最適化）

### 開発者ツールAPI
- `GET /api/developer/export-all-geojson` - 全データGeoJSONエクスポート
- `GET /api/developer/export-optimized-geojson` - 最適化・サンプリングエクスポート
- `GET /api/developer/database-stats` - データベース統計情報

## 技術スタック

**バックエンド**
- FastAPI - 高性能Python Webフレームワーク
- PostgreSQL - メインデータベース（高速COPY処理）
- Supabase - 認証・ユーザー管理
- JWT - セキュアなトークンベース認証

**フロントエンド** 
- Deck.gl - WebGL地図可視化ライブラリ（GPU活用）
- Vanilla JavaScript - 軽量・高速フロントエンド
- Tailwind CSS - レスポンシブデザイン
- モバイル対応 - スマートフォン・タブレット最適化

**デプロイ・運用**
- Docker - コンテナ化によるポータブル実行環境
- 本番環境 - https://pathfinder.dk-core.com
- 1GBメモリ最適化設計

## パフォーマンス特徴

- **大容量データ対応**: 15万件以上のTimelineポイントを快適表示
- **ズーム最適化**: レベル別データフィルタリング（≤8: 50%表示 → ≥14: 100%表示）
- **WebGL レンダリング**: GPU活用による滑らかなマップ操作・60FPS
- **高速インポート**: PostgreSQL COPYで15万レコード/秒の処理速度
- **モバイル最適化**: 折りたたみパネル・タッチフレンドリーUI
- **メモリ効率**: 1GBメモリ環境での安定動作

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