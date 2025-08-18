"""
Timeline Parser Configuration
タイムラインパーサーの設定を管理するモジュール
"""

import os

# データベース設定
DATABASE_CONFIG = {
    "auto_create_table": True,
    "batch_size": 1000,  # バッチ挿入のサイズ
    "connection_timeout": 30
}

# タイムゾーン設定
INPUT_TIMEZONE = "Asia/Tokyo"
OUTPUT_TIMEZONE = "UTC"

# データ検証設定
VALIDATION_CONFIG = {
    "max_latitude": 90.0,
    "min_latitude": -90.0,
    "max_longitude": 180.0,
    "min_longitude": -180.0,
    "max_distance_meters": 1000000,  # 1000km
    "min_probability": 0.0,
    "max_probability": 1.0
}

# エラーハンドリング設定
ERROR_CONFIG = {
    "strict_mode": False,  # 厳密モード（エラー時に処理を停止）
    "log_errors": True,    # エラーログの記録
    "skip_invalid_records": True  # 無効なレコードをスキップ
}

# データ形式検出パターン
DETECTION_PATTERNS = {
    "android": {
        "required_fields": ["semanticSegments"],
        "optional_fields": ["timelinePath", "visit", "activity"],
        "description": "Android Google Timeline形式"
    },
    "iphone": {
        "required_fields": ["startTime"],
        "structure": "array",
        "description": "iPhone Google Timeline形式"
    }
}

# ファイルアップロード設定
UPLOAD_CONFIG = {
    "max_file_size": int(os.getenv("UPLOAD_MAX_SIZE", "100")) * 1024 * 1024,  # 100MB
    "allowed_extensions": [".json", ".gpx"],
    "allowed_mime_types": ["application/json", "text/plain", "application/gpx+xml", "application/xml"]
}

# パフォーマンス設定
PERFORMANCE_CONFIG = {
    "chunk_size": int(os.getenv("BATCH_SIZE", "5000")),  # 大きなファイルの分割サイズ
    "memory_limit_mb": 1000,  # メモリ使用量の上限
    "progress_update_interval": 1000  # 進捗表示の更新間隔
}

# デバッグ設定
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
VERBOSE_LOGGING = False