# メモリ最適化計画

## 現在の問題

### メモリ制約
- **アプリサーバー**: 1GB制限
- **PostgreSQLサーバー**: 1GB（別マシン・問題なし）

### 危険な処理
1. **Timeline アップロード** (`api/timeline/upload.py`)
   - 大量JSON（100MB+）を全てメモリ展開
   - 15万レコード処理時: 300-500MB使用

2. **マップデータ取得** (`api/database.py`)
   - 大量レコードを一度にfetchall()
   - JSON変換でメモリ倍増

## 最適化方針

### 1. ストリーミング処理の実装

#### JSONファイル読み込み
```python
import ijson  # 追加ライブラリ

async def read_json_streaming(file: UploadFile):
    parser = ijson.parse(file.file)
    for prefix, event, value in parser:
        if prefix.endswith('.timelineObjects.item'):
            yield value  # 1件ずつ処理
```

#### チャンク単位データベース処理
```python
def copy_chunk_to_db(records, chunk_size=1000):
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        # 小単位でCOPY処理
        copy_string = StringIO()
        for record in chunk:
            copy_string.write(f"{record}\\n")
        cursor.copy_from(copy_string, 'timeline_data')
```

### 2. マップデータのページネーション

#### 現在の問題
```python
# 全データを一度に取得・返却
rows = cur.fetchall()  # 数十万件
return [{"lat": row[0], ...} for row in rows]  # 数百MB
```

#### 最適化案
```python
# LIMIT/OFFSET でページング
query = f"SELECT ... FROM timeline_data WHERE ... LIMIT {limit} OFFSET {offset}"
# またはカーソルベースページング
```

### 3. メモリ使用量目標

| 処理 | 現在 | 最適化後 |
|-----|------|---------|
| アプリ基本動作 | 200MB | 200MB |
| Timeline アップロード | 300-500MB | 50MB |
| マップデータ取得 | 100-300MB | 30MB |
| **合計最大** | **800MB** | **280MB** |

## 実装ステップ

### Phase 1: ストリーミングアップロード
1. `ijson` ライブラリ追加
2. `upload.py` でチャンク処理実装
3. 進捗表示UI追加（オプション）

### Phase 2: データ取得最適化
1. マップAPI のページネーション
2. ズームレベル別データ制限強化
3. レスポンスサイズ監視

### Phase 3: Docker最適化
1. メモリ制限設定
2. ワーカー数調整
3. ガベージコレクション設定

## 緊急時の対策

### 即座に適用可能
1. **データ制限**: マップ表示件数を強制的に制限
2. **アップロードサイズ制限**: FastAPIでファイルサイズ上限設定
3. **Docker制限**: メモリ制限でプロセス保護

```python
# 緊急制限例
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
MAX_MAP_POINTS = 50000  # 5万件まで
```

## 監視項目

1. **メモリ使用量**: プロセス監視
2. **アップロードファイルサイズ**: ログ記録
3. **データベースレスポンス時間**: パフォーマンス監視
4. **エラー率**: OOM(Out of Memory)エラー検知

## 備考

- PostgreSQLサーバー側は問題なし（別マシン1GB）
- 主な最適化対象はアプリサーバーのメモリ管理
- ユーザー体験を損なわない範囲での段階的実装を推奨