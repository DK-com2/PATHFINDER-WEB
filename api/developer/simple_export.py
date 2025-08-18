from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from typing import Optional
import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from utils.database import get_db_connection

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

DEVELOPER_PASSWORD = os.getenv("DEVELOPER_PASSWORD", "change-this-password")

@router.post("/verify-password")
async def verify_developer_password(password_data: dict):
    """開発者パスワードを確認"""
    password = password_data.get("password", "")
    
    if password == DEVELOPER_PASSWORD:
        return {"valid": True, "message": "認証成功"}
    else:
        return {"valid": False, "message": "パスワードが正しくありません"}

@router.get("/export-all-data")
async def export_all_data(password: str, thin_rate: float = 1.0, start_date: str = None, end_date: str = None):
    """全データをGeoJSON形式でエクスポート"""
    
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 基本条件
        conditions = [
            "latitude IS NOT NULL",
            "longitude IS NOT NULL", 
            "latitude BETWEEN -90 AND 90",
            "longitude BETWEEN -180 AND 180",
            "NOT (latitude = 0 AND longitude = 0)"
        ]
        params = []
        
        # 期間フィルタを追加
        if start_date:
            conditions.append("start_time >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("start_time <= %s")
            params.append(end_date)
        
        query = f"""
            SELECT id, type, start_time, end_time, point_time, 
                   latitude, longitude, visit_probability, visit_placeid, 
                   visit_semantictype, activity_distancemeters, activity_type, 
                   activity_probability, username, _gpx_data_source, 
                   _gpx_track_name, _gpx_elevation, _gpx_speed, _gpx_point_sequence
            FROM timeline_data 
            WHERE {' AND '.join(conditions)}
            ORDER BY username, start_time DESC
        """
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        columns = [desc[0] for desc in cur.description]
        
        features = []
        invalid_count = 0
        thinned_count = 0
        
        # 間引き処理：thin_rate が1.0未満の場合のみ適用
        if thin_rate < 1.0:
            import random
            random.seed(42)  # 一貫した結果のために固定シード
            step = int(1 / thin_rate) if thin_rate > 0 else 1
            
        for i, row in enumerate(rows):
            try:
                row_dict = {}
                for j, value in enumerate(row):
                    if value is not None:
                        if hasattr(value, 'isoformat'):
                            row_dict[columns[j]] = value.isoformat()
                        else:
                            row_dict[columns[j]] = value
                
                # timelinePathのみ間引き処理を適用
                data_type = row_dict.get('type')
                if thin_rate < 1.0 and data_type == 'timelinePath':
                    if i % step != 0:
                        thinned_count += 1
                        continue
                
                lat = row_dict.get('latitude')
                lng = row_dict.get('longitude')
                
                if lat is None or lng is None:
                    invalid_count += 1
                    continue
                
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    invalid_count += 1
                    continue
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lng), float(lat)]
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
        
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_features": len(features),
                "invalid_records": invalid_count,
                "thinned_records": thinned_count,
                "thin_rate": thin_rate,
                "date_filter": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "exported_by": "pathfinder-web-simple-export"
            },
            "features": features
        }
        
        geojson_content = json.dumps(geojson, ensure_ascii=False, indent=2)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pathfinder_all_data_{timestamp}.geojson"
        
        logger.info(f"Exported {len(features)} features to GeoJSON (skipped {invalid_count} invalid, {thinned_count} timelinePath thinned records, thin_rate={thin_rate})")
        
        return Response(
            content=geojson_content,
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export all data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export-user-data")
async def export_user_data(password: str, username: str):
    """特定ユーザーのデータをGeoJSON形式でエクスポート"""
    
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    # URL デコーディングを実行
    from urllib.parse import unquote
    username = unquote(username)
    logger.info(f"Processing export for user: {repr(username)}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT id, type, start_time, end_time, point_time, 
                   latitude, longitude, visit_probability, visit_placeid, 
                   visit_semantictype, activity_distancemeters, activity_type, 
                   activity_probability, username, _gpx_data_source, 
                   _gpx_track_name, _gpx_elevation, _gpx_speed, _gpx_point_sequence
            FROM timeline_data 
            WHERE username = %s
              AND latitude IS NOT NULL 
              AND longitude IS NOT NULL 
              AND latitude BETWEEN -90 AND 90 
              AND longitude BETWEEN -180 AND 180
              AND NOT (latitude = 0 AND longitude = 0)
            ORDER BY start_time DESC
        """
        
        cur.execute(query, (username,))
        rows = cur.fetchall()
        
        columns = [desc[0] for desc in cur.description]
        
        features = []
        invalid_count = 0
        
        for row in rows:
            try:
                row_dict = {}
                for i, value in enumerate(row):
                    if value is not None:
                        if hasattr(value, 'isoformat'):
                            row_dict[columns[i]] = value.isoformat()
                        else:
                            row_dict[columns[i]] = value
                
                lat = row_dict.get('latitude')
                lng = row_dict.get('longitude')
                
                if lat is None or lng is None:
                    invalid_count += 1
                    continue
                
                if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                    invalid_count += 1
                    continue
                
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lng), float(lat)]
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
        
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "username": username,
                "total_features": len(features),
                "invalid_records": invalid_count,
                "exported_by": "pathfinder-web-simple-export"
            },
            "features": features
        }
        
        geojson_content = json.dumps(geojson, ensure_ascii=False, indent=2)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # ファイル名をASCII安全な形式に変換
        import re
        import hashlib
        
        # 日本語文字を含む場合は、ハッシュを使用してASCII文字のみにする
        try:
            # ASCII文字のみかチェック
            username.encode('ascii')
            # ASCII文字のみの場合は、非ASCII文字を_に置換
            safe_username = re.sub(r'[^\w\-_.]', '_', username)
        except UnicodeEncodeError:
            # 日本語等の非ASCII文字が含まれる場合は、ハッシュを使用
            username_hash = hashlib.md5(username.encode('utf-8')).hexdigest()[:8]
            safe_username = f"user_{username_hash}"
        
        # 空になった場合のフォールバック
        if not safe_username or safe_username == '_':
            safe_username = 'user'
        
        filename = f"pathfinder_{safe_username}_{timestamp}.geojson"
        
        logger.info(f"Exported {len(features)} features for user {username}")
        logger.info(f"Generated filename: {filename}")
        
        return Response(
            content=geojson_content.encode('utf-8'),
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export user data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/get-users")
async def get_available_users(password: str):
    """利用可能なユーザー一覧を取得"""
    
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT username, COUNT(*) as count,
                   MIN(start_time) as first_data,
                   MAX(start_time) as last_data
            FROM timeline_data 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY username 
            ORDER BY count DESC
        """)
        
        users = []
        for row in cur.fetchall():
            username, count, first_data, last_data = row
            users.append({
                "username": username,
                "record_count": count,
                "first_data": first_data.isoformat() if first_data else None,
                "last_data": last_data.isoformat() if last_data else None
            })
        
        cur.close()
        conn.close()
        
        return {"users": users}
        
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@router.get("/database-stats")
async def get_database_stats(password: str):
    """データベース統計情報を取得"""
    
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
        
        # 全体の期間情報
        cur.execute("""
            SELECT MIN(start_time) as min_date, MAX(start_time) as max_date 
            FROM timeline_data 
            WHERE start_time IS NOT NULL
        """)
        date_range = cur.fetchone()
        
        # データタイプ別統計
        cur.execute("""
            SELECT type, COUNT(*) as count 
            FROM timeline_data 
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            GROUP BY type 
            ORDER BY count DESC
        """)
        type_stats = dict(cur.fetchall())
        
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