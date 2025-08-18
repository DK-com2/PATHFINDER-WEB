from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from typing import Dict, Any
import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from utils.database import get_db_connection

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

# 開発者パスワード
DEVELOPER_PASSWORD = os.getenv("DEVELOPER_PASSWORD", "change-this-password")

@router.post("/verify-password")
async def verify_developer_password(password_data: dict):
    """開発者パスワードを確認"""
    password = password_data.get("password", "")
    
    if password == DEVELOPER_PASSWORD:
        return {"valid": True, "message": "認証成功"}
    else:
        return {"valid": False, "message": "パスワードが正しくありません"}

@router.get("/export-all-geojson")
async def export_all_timeline_geojson(password: str):
    """全タイムラインデータをGeoJSON形式でエクスポート"""
    
    # パスワード確認
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    try:
        # PostgreSQLから全データ取得
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 座標データが存在するレコードのみを取得
        query = """
            SELECT id, type, start_time, end_time, point_time, 
                   latitude, longitude, visit_probability, visit_placeid, 
                   visit_semantictype, activity_distancemeters, activity_type, 
                   activity_probability, username, _gpx_data_source, 
                   _gpx_track_name, _gpx_elevation, _gpx_speed, _gpx_point_sequence
            FROM timeline_data 
            WHERE latitude IS NOT NULL 
              AND longitude IS NOT NULL 
              AND latitude BETWEEN -90 AND 90 
              AND longitude BETWEEN -180 AND 180
              AND NOT (latitude = 0 AND longitude = 0)
            ORDER BY username, start_time DESC
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        # カラム名を取得
        columns = [desc[0] for desc in cur.description]
        
        # GeoJSON features作成
        features = []
        invalid_count = 0
        
        for row in rows:
            try:
                row_dict = {}
                for i, value in enumerate(row):
                    if value is not None:
                        if hasattr(value, 'isoformat'):  # datetime
                            row_dict[columns[i]] = value.isoformat()
                        else:
                            row_dict[columns[i]] = value
                
                lat = row_dict.get('latitude')
                lng = row_dict.get('longitude')
                
                # 座標の妥当性チェック
                if lat is None or lng is None:
                    invalid_count += 1
                    continue
                
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    invalid_count += 1
                    continue
                
                # GeoJSON Feature作成
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lng), float(lat)]  # [longitude, latitude]
                    },
                    "properties": row_dict
                }
                
                features.append(feature)
                
            except Exception as e:
                logger.warning(f"Skipping invalid row: {e}")
                invalid_count += 1
                continue
        
        cur.close()
        conn.close()
        
        # GeoJSON作成
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_features": len(features),
                "invalid_records": invalid_count,
                "exported_by": "pathfinder-web-developer-tools"
            },
            "features": features
        }
        
        # JSONシリアライズ
        geojson_content = json.dumps(geojson, ensure_ascii=False, indent=2)
        
        # ファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pathfinder_timeline_data_{timestamp}.geojson"
        
        logger.info(f"Exported {len(features)} features to GeoJSON (skipped {invalid_count} invalid records)")
        
        # ファイルダウンロードレスポンス
        return Response(
            content=geojson_content,
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export GeoJSON: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/database-stats")
async def get_database_stats(password: str):
    """データベース統計情報を取得（開発者用）"""
    
    # パスワード確認
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 全レコード数
        cur.execute("SELECT COUNT(*) FROM timeline_data")
        total_count = cur.fetchone()[0]
        
        # 座標データ有りレコード数
        cur.execute("""
            SELECT COUNT(*) FROM timeline_data 
            WHERE latitude IS NOT NULL 
              AND longitude IS NOT NULL 
              AND latitude BETWEEN -90 AND 90 
              AND longitude BETWEEN -180 AND 180
              AND NOT (latitude = 0 AND longitude = 0)
        """)
        valid_coordinates_count = cur.fetchone()[0]
        
        # ユーザー別統計
        cur.execute("""
            SELECT username, COUNT(*) as count 
            FROM timeline_data 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY username 
            ORDER BY count DESC
        """)
        user_stats = dict(cur.fetchall())
        
        # データタイプ別統計
        cur.execute("""
            SELECT type, COUNT(*) as count 
            FROM timeline_data 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY type
        """)
        type_stats = dict(cur.fetchall())
        
        # 日付範囲
        cur.execute("""
            SELECT MIN(start_time) as min_date, MAX(start_time) as max_date 
            FROM timeline_data 
            WHERE start_time IS NOT NULL
        """)
        date_range = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "database_stats": {
                "total_records": total_count,
                "valid_coordinates": valid_coordinates_count,
                "invalid_coordinates": total_count - valid_coordinates_count,
                "date_range": {
                    "start": date_range[0].isoformat() if date_range[0] else None,
                    "end": date_range[1].isoformat() if date_range[1] else None
                } if date_range else None,
                "user_stats": user_stats,
                "type_stats": type_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")