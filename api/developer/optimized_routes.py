from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import Dict, Any, Optional, List
import json
import logging
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from urllib.parse import unquote

from utils.database import get_db_connection

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

DEVELOPER_PASSWORD = os.getenv("DEVELOPER_PASSWORD", "change-this-password")

@router.get("/export-optimized-geojson")
async def export_optimized_geojson(
    password: str,
    limit: Optional[int] = Query(10000, description="最大レコード数"),
    days: Optional[int] = Query(30, description="過去N日のデータ"),
    users: Optional[str] = Query(None, description="ユーザー名（カンマ区切り）"),
    sample_rate: Optional[float] = Query(1.0, description="サンプリング率 (0.1-1.0)")
):
    """最適化されたGeoJSONエクスポート（ファイルサイズ削減版）"""
    
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 条件構築
        conditions = []
        params = []
        
        # 基本条件
        conditions.extend([
            "latitude IS NOT NULL",
            "longitude IS NOT NULL", 
            "latitude BETWEEN -90 AND 90",
            "longitude BETWEEN -180 AND 180",
            "NOT (latitude = 0 AND longitude = 0)"
        ])
        
        # 日数制限
        if days:
            date_limit = datetime.now() - timedelta(days=days)
            conditions.append("start_time >= %s")
            params.append(date_limit)
        
        # ユーザー制限
        if users:
            user_list = [u.strip() for u in users.split(',')]
            placeholders = ','.join(['%s'] * len(user_list))
            conditions.append(f"username IN ({placeholders})")
            params.extend(user_list)
        
        # サンプリング（PostgreSQLのTABLESAMPLE使用）
        sample_clause = ""
        if 0.1 <= sample_rate < 1.0:
            sample_percent = sample_rate * 100
            sample_clause = f"TABLESAMPLE SYSTEM ({sample_percent})"
        
        # クエリ構築（最小限のカラムのみ選択）
        query = f"""
            SELECT 
                latitude, longitude, type, username,
                EXTRACT(EPOCH FROM start_time) as start_timestamp,
                visit_semantictype, activity_type
            FROM timeline_data {sample_clause}
            WHERE {' AND '.join(conditions)}
            ORDER BY start_time DESC 
            LIMIT %s
        """
        
        params.append(limit)
        cur.execute(query, params)
        rows = cur.fetchall()
        
        # 軽量GeoJSON作成
        features = []
        for row in rows:
            lat, lng, data_type, username, start_timestamp, visit_type, activity_type = row
            
            # 最小限のプロパティ
            properties = {
                "u": username,  # 短縮キー
                "t": data_type,
                "ts": int(start_timestamp) if start_timestamp else None
            }
            
            # タイプ別の追加情報（最小限）
            if visit_type:
                properties["v"] = visit_type
            if activity_type:
                properties["a"] = activity_type
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(float(lng), 6), round(float(lat), 6)]  # 精度削減
                },
                "properties": properties
            }
            features.append(feature)
        
        cur.close()
        conn.close()
        
        # 軽量GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # ファイル名生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{sample_rate}sample" if sample_rate < 1.0 else ""
        filename = f"pathfinder_optimized{suffix}_{timestamp}.geojson"
        
        # 圧縮JSON（改行・スペースなし）
        geojson_content = json.dumps(geojson, ensure_ascii=False, separators=(',', ':'))
        
        file_size_mb = len(geojson_content.encode('utf-8')) / 1024 / 1024
        logger.info(f"Exported {len(features)} features, file size: {file_size_mb:.1f}MB")
        
        return Response(
            content=geojson_content,
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-File-Size-MB": str(round(file_size_mb, 1)),
                "X-Feature-Count": str(len(features))
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export optimized GeoJSON: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.get("/export-by-user-geojson")
async def export_by_user_geojson(password: str, username: str):
    """特定ユーザーのデータのみをエクスポート"""
    
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    # URL decodingを実行
    username = unquote(username)
    logger.info(f"Processing export for user: {repr(username)}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT latitude, longitude, type, start_time, end_time,
                   visit_semantictype, activity_type, visit_probability, activity_probability
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
        
        features = []
        for row in rows:
            lat, lng, data_type, start_time, end_time, visit_type, activity_type, visit_prob, activity_prob = row
            
            properties = {
                "type": data_type,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "username": username
            }
            
            if visit_type:
                properties["visit_semantictype"] = visit_type
                if visit_prob:
                    properties["visit_probability"] = float(visit_prob)
            
            if activity_type:
                properties["activity_type"] = activity_type
                if activity_prob:
                    properties["activity_probability"] = float(activity_prob)
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lng), float(lat)]
                },
                "properties": properties
            }
            features.append(feature)
        
        cur.close()
        conn.close()
        
        geojson = {
            "type": "FeatureCollection",
            "metadata": {
                "username": username,
                "export_timestamp": datetime.now().isoformat(),
                "total_features": len(features)
            },
            "features": features
        }
        
        geojson_content = json.dumps(geojson, ensure_ascii=True, indent=2)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # ファイル名をASCII安全な形式に変換
        safe_username = re.sub(r'[^\w\-_.]', '_', username)
        filename = f"pathfinder_{safe_username}_{timestamp}.geojson"
        
        logger.info(f"Generated filename: {filename}")
        logger.info(f"Content length: {len(geojson_content)} bytes")
        
        return Response(
            content=geojson_content.encode('utf-8'),
            media_type="application/geo+json",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\""
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export user GeoJSON: {e}")
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

@router.get("/estimate-file-size")
async def estimate_file_size(
    password: str,
    limit: Optional[int] = Query(10000),
    days: Optional[int] = Query(30),
    users: Optional[str] = Query(None),
    sample_rate: Optional[float] = Query(1.0)
):
    """エクスポートファイルサイズを事前推定"""
    
    if password != DEVELOPER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid password")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 条件に基づく推定レコード数を取得
        conditions = [
            "latitude IS NOT NULL",
            "longitude IS NOT NULL"
        ]
        params = []
        
        if days:
            date_limit = datetime.now() - timedelta(days=days)
            conditions.append("start_time >= %s")
            params.append(date_limit)
        
        if users:
            user_list = [u.strip() for u in users.split(',')]
            placeholders = ','.join(['%s'] * len(user_list))
            conditions.append(f"username IN ({placeholders})")
            params.extend(user_list)
        
        count_query = f"""
            SELECT COUNT(*) FROM timeline_data 
            WHERE {' AND '.join(conditions)}
        """
        
        cur.execute(count_query, params)
        total_records = cur.fetchone()[0]
        
        # サンプリングとlimit適用後の推定件数
        estimated_records = min(int(total_records * sample_rate), limit)
        
        # 1レコードあたりの平均サイズ（バイト）を推定
        avg_bytes_per_record = 150  # 経験値
        estimated_size_bytes = estimated_records * avg_bytes_per_record
        estimated_size_mb = estimated_size_bytes / 1024 / 1024
        
        cur.close()
        conn.close()
        
        return {
            "total_available_records": total_records,
            "estimated_export_records": estimated_records,
            "estimated_size_mb": round(estimated_size_mb, 1),
            "within_mapbox_limit": estimated_size_mb <= 300,
            "parameters": {
                "limit": limit,
                "days": days,
                "users": users,
                "sample_rate": sample_rate
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to estimate file size: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to estimate: {str(e)}")