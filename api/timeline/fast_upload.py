"""
Fast Upload API
COPY文を使った超高速アップロード処理
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
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


@router.post("/fast-upload")
async def fast_upload_timeline_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """COPY文を使った超高速タイムラインファイルアップロード"""
    
    # 基本的な検証は通常のuploadと同じ
    if file.size and file.size > UPLOAD_CONFIG["max_file_size"]:
        raise HTTPException(
            status_code=413,
            detail=f"ファイルサイズが上限を超えています"
        )
    
    file_extension = os.path.splitext(file.filename.lower())[1] if file.filename else ""
    if file_extension != ".json":
        raise HTTPException(status_code=400, detail="JSONファイルのみ対応しています")
    
    try:
        logger.info(f"高速アップロード開始: {file.filename}, サイズ: {file.size}")
        
        # ユーザー名を取得
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            raise HTTPException(status_code=400, detail="ユーザー名が設定されていません")
        
        username = username_response.data[0]["username"]
        
        # ストリーミング処理でレコードを生成・保存
        parser = TimelineJSONParser()
        records_generator = parser.parse_json_stream(file.file, username)
        
        BATCH_SIZE = 1000
        batch = []
        total_saved = 0
        total_records = 0
        
        for record in records_generator:
            batch.append(record)
            total_records += 1

            if len(batch) >= BATCH_SIZE:
                saved_count = await _save_records_with_copy(batch)
                total_saved += saved_count
                batch = []
        
        if batch:
            saved_count = await _save_records_with_copy(batch)
            total_saved += saved_count

        if total_records == 0:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "有効なレコードが見つかりませんでした"
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "データの処理が完了しました",
                "filename": file.filename,
                "total_records": total_records,
                "saved_records": total_saved,
                "username": username,
                "method": "COPY (超高速・ストリーミング)"
            }
        )
        
    except Exception as e:
        logger.error(f"高速アップロードエラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"処理に失敗しました: {str(e)}")


async def _save_records_with_copy(records: list) -> int:
    """COPY文を使った超高速レコード保存"""
    try:
        logger.info(f"COPY文による超高速保存開始: {len(records)}レコード")
        
        # CSVデータをメモリ上で準備
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer, delimiter='\t')  # TAB区切り
        
        for record in records:
            # ジオメトリデータの作成 (EWKT形式: SRID=4326;POINT(lng lat))
            geom = ''
            if record.get('latitude') and record.get('longitude'):
                try:
                    lng = float(record['longitude'])
                    lat = float(record['latitude'])
                    geom = f'SRID=4326;POINT({lng} {lat})'
                except (ValueError, TypeError):
                    pass

            csv_writer.writerow([
                record.get('type'),
                record.get('start_time'),
                record.get('end_time'),
                record.get('point_time'),
                record.get('latitude'),
                record.get('longitude'),
                record.get('visit_probability'),
                record.get('visit_placeId'),
                record.get('visit_semanticType'),
                record.get('activity_distanceMeters'),
                record.get('activity_type'),
                record.get('activity_probability'),
                record.get('username'),
                record.get('_gpx_data_source'),
                record.get('_gpx_track_name'),
                record.get('_gpx_elevation'),
                record.get('_gpx_speed'),
                record.get('_gpx_point_sequence'),
                geom # geomカラムを追加
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
                _gpx_speed, _gpx_point_sequence, geom
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