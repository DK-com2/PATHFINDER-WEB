"""
Timeline Upload API
ファイルアップロードとパースのAPIエンドポイント
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
import json
import logging
import tempfile
import os
import csv
import io
from supabase import create_client

from api.auth import get_current_user
from services.timeline.json_parser import TimelineJSONParser
from services.timeline.config import UPLOAD_CONFIG, DEBUG
from utils.database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload")
async def upload_timeline_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """タイムラインファイルをアップロードして解析・保存"""
    
    # ファイルサイズチェック
    if file.size and file.size > UPLOAD_CONFIG["max_file_size"]:
        raise HTTPException(
            status_code=413,
            detail=f"ファイルサイズが上限を超えています: {file.size / 1024 / 1024:.1f}MB > {UPLOAD_CONFIG['max_file_size'] / 1024 / 1024:.1f}MB"
        )
    
    # ファイル拡張子チェック
    file_extension = os.path.splitext(file.filename.lower())[1] if file.filename else ""
    if file_extension not in UPLOAD_CONFIG["allowed_extensions"]:
        raise HTTPException(
            status_code=400,
            detail=f"未対応のファイル形式です: {file_extension}。対応形式: {', '.join(UPLOAD_CONFIG['allowed_extensions'])}"
        )
    
    # MIMEタイプチェック
    if file.content_type and file.content_type not in UPLOAD_CONFIG["allowed_mime_types"]:
        raise HTTPException(
            status_code=400,
            detail=f"未対応のMIMEタイプです: {file.content_type}"
        )
    
    try:
        logger.info(f"アップロード開始: {file.filename}, サイズ: {file.size}, タイプ: {file.content_type}")
        
        # ユーザー名を取得
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            raise HTTPException(status_code=400, detail="ユーザー名が設定されていません")
        
        username = username_response.data[0]["username"]
        logger.info(f"ユーザー名取得成功: {username}")
        
        # ファイル内容を読み取り
        content = await file.read()
        logger.info(f"ファイル読み取り完了: {len(content)} bytes")
        
        # JSONファイルの場合のみ対応（今回はJSONのみ実装）
        if file_extension == ".json":
            return await _process_json_file(content, username, file.filename)
        else:
            raise HTTPException(status_code=400, detail="現在はJSONファイルのみ対応しています")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイル処理エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ファイル処理に失敗しました: {str(e)}")


async def _process_json_file(content: bytes, username: str, filename: str) -> JSONResponse:
    """JSONファイルを処理してデータベースに保存"""
    try:
        logger.info(f"JSON処理開始: {filename}")
        
        # JSONデータを解析
        json_data = json.loads(content.decode('utf-8'))
        logger.info(f"JSON解析完了: データタイプ = {type(json_data)}")
        
        # JSONパーサーを使用してレコードを生成
        parser = TimelineJSONParser()
        logger.info("パーサー初期化完了")
        
        records = parser.parse_json_data(json_data, username)
        logger.info(f"レコード生成完了: {len(records)}件")
        
        if not records:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "有効なレコードが見つかりませんでした",
                    "validation_summary": parser.get_parsing_summary()
                }
            )
        
        # COPY文で超高速データベース保存
        logger.info("超高速データベース保存開始")
        saved_count = await _save_records_with_copy(records)
        logger.info(f"COPY文による超高速保存完了: {saved_count}件")
        
        validation_summary = parser.get_parsing_summary()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"データの処理が完了しました",
                "filename": filename,
                "total_records": len(records),
                "saved_records": saved_count,
                "username": username,
                "validation_summary": validation_summary
            }
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析エラー: {e}")
        raise HTTPException(status_code=400, detail=f"JSONファイルの解析に失敗しました: {str(e)}")
    except Exception as e:
        logger.error(f"JSON処理エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"JSON処理に失敗しました: {str(e)}")


async def _save_records_with_copy(records: list) -> int:
    """COPY文を使った超高速レコード保存"""
    try:
        logger.info(f"COPY文による超高速保存開始: {len(records)}レコード")
        
        # CSVデータをメモリ上で準備
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer, delimiter='\t')  # TAB区切り
        
        for record in records:
            csv_writer.writerow([
                record.get('type') or '',
                record.get('start_time') or '',
                record.get('end_time') or '',
                record.get('point_time') or '',
                record.get('latitude') or '',
                record.get('longitude') or '',
                record.get('visit_probability') or '',
                record.get('visit_placeId') or '',
                record.get('visit_semanticType') or '',
                record.get('activity_distanceMeters') or '',
                record.get('activity_type') or '',
                record.get('activity_probability') or '',
                record.get('username') or '',
                record.get('_gpx_data_source') or '',
                record.get('_gpx_track_name') or '',
                record.get('_gpx_elevation') or '',
                record.get('_gpx_speed') or '',
                record.get('_gpx_point_sequence') or ''
            ])
        
        logger.info("CSV データ準備完了")
        
        # データベース接続
        conn = get_db_connection()
        cur = conn.cursor()
        
        # CSV バッファを先頭に戻す
        csv_buffer.seek(0)
        
        # COPY文で一括挿入
        copy_sql = """
            COPY timeline_data (
                type, start_time, end_time, point_time, latitude, longitude,
                visit_probability, visit_placeid, visit_semantictype,
                activity_distancemeters, activity_type, activity_probability,
                username, _gpx_data_source, _gpx_track_name, _gpx_elevation,
                _gpx_speed, _gpx_point_sequence
            ) FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', NULL '')
        """
        
        logger.info("COPY文実行開始")
        cur.copy_expert(copy_sql, csv_buffer)
        
        saved_count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"COPY文による超高速保存完了: {saved_count}レコード")
        return saved_count
        
    except Exception as e:
        logger.error(f"COPY文保存エラー: {e}", exc_info=True)
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise


@router.delete("/clear-data")
async def clear_user_timeline_data(current_user: dict = Depends(get_current_user)):
    """ユーザーのタイムラインデータを全削除"""
    try:
        # ユーザー名を取得
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            raise HTTPException(status_code=400, detail="ユーザー名が設定されていません")
        
        username = username_response.data[0]["username"]
        logger.info(f"データ削除開始: ユーザー名 = {username}")
        
        # データベース接続
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 削除前にレコード数を取得
        cur.execute("SELECT COUNT(*) FROM timeline_data WHERE username = %s", (username,))
        record_count = cur.fetchone()[0]
        
        # ユーザーのデータを削除
        cur.execute("DELETE FROM timeline_data WHERE username = %s", (username,))
        deleted_count = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"データ削除完了: {deleted_count}レコード削除")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "データが正常に削除されました",
                "username": username,
                "deleted_records": deleted_count,
                "verified_count": record_count
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"データ削除エラー: {e}", exc_info=True)
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise HTTPException(status_code=500, detail=f"データ削除に失敗しました: {str(e)}")


@router.get("/formats")
async def get_supported_formats(current_user: dict = Depends(get_current_user)):
    """対応しているファイル形式の一覧を取得"""
    return {
        "supported_formats": {
            "json": {
                "extensions": [".json"],
                "mime_types": ["application/json", "text/plain"],
                "description": "Google Timeline JSON (Android/iPhone対応)",
                "max_size_mb": UPLOAD_CONFIG["max_file_size"] / 1024 / 1024
            }
        },
        "future_support": {
            "gpx": {
                "extensions": [".gpx"],
                "mime_types": ["application/gpx+xml", "application/xml"],
                "description": "GPX Track Files (実装予定)"
            }
        }
    }