from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging
import os
from datetime import datetime
from supabase import create_client

from api.auth import get_current_user
from utils.database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/timeline-points")
async def get_timeline_points(
    current_user: dict = Depends(get_current_user),
    limit: Optional[int] = None
):
    """認証されたユーザーのタイムラインデータを軽量JSON形式で配信"""
    try:
        # Get username from Supabase
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        # Get username
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            return {"total": 0, "data": [], "message": "Username not set"}
        
        username = username_response.data[0]["username"]
        
        # Get lightweight timeline data from PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 必要最小限のカラムのみ取得して軽量化
        if limit:
            query = """
                SELECT latitude, longitude, type, start_time, 
                       visit_semantictype, activity_type
                FROM timeline_data 
                WHERE username = %s 
                  AND latitude IS NOT NULL 
                  AND longitude IS NOT NULL 
                  AND latitude BETWEEN -90 AND 90 
                  AND longitude BETWEEN -180 AND 180
                  AND NOT (latitude = 0 AND longitude = 0)
                ORDER BY start_time DESC 
                LIMIT %s
            """
            cur.execute(query, (username, limit))
        else:
            query = """
                SELECT latitude, longitude, type, start_time, 
                       visit_semantictype, activity_type
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
        
        # 軽量JSON形式に変換
        data = []
        for row in rows:
            lat, lng, data_type, start_time, semantic_type, activity_type = row
            
            point = {
                "lat": float(lat),
                "lng": float(lng),
                "type": data_type,
                "time": start_time.isoformat() if start_time else None
            }
            
            # 必要な場合のみ追加フィールドを含める
            if semantic_type:
                point["semantic"] = semantic_type
            if activity_type:
                point["activity"] = activity_type
                
            data.append(point)
        
        cur.close()
        conn.close()
        
        logger.info(f"Delivered {len(data)} timeline points for user {username}")
        
        return {
            "total": len(data),
            "username": username,
            "data": data
        }
        
    except Exception as e:
        logger.error(f"Failed to get timeline points: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get timeline points: {str(e)}")

@router.get("/timeline-stats")
async def get_timeline_stats(current_user: dict = Depends(get_current_user)):
    """認証されたユーザーのタイムラインデータ統計情報を取得"""
    try:
        # Get username from Supabase
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        # Get username
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            return {"message": "Username not set", "stats": {}}
        
        username = username_response.data[0]["username"]
        
        # Get stats from PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 総データ数
        cur.execute("""
            SELECT COUNT(*) FROM timeline_data 
            WHERE username = %s 
              AND latitude IS NOT NULL 
              AND longitude IS NOT NULL
        """, (username,))
        total_points = cur.fetchone()[0]
        
        # データタイプ別統計
        cur.execute("""
            SELECT type, COUNT(*) as count 
            FROM timeline_data 
            WHERE username = %s 
              AND latitude IS NOT NULL 
              AND longitude IS NOT NULL
            GROUP BY type 
            ORDER BY count DESC
        """, (username,))
        type_stats = dict(cur.fetchall())
        
        # 日付範囲
        cur.execute("""
            SELECT MIN(start_time) as min_date, MAX(start_time) as max_date 
            FROM timeline_data 
            WHERE username = %s AND start_time IS NOT NULL
        """, (username,))
        date_range = cur.fetchone()
        
        cur.close()
        conn.close()
        
        stats = {
            "total_points": total_points,
            "username": username,
            "type_distribution": type_stats,
            "date_range": {
                "start": date_range[0].isoformat() if date_range[0] else None,
                "end": date_range[1].isoformat() if date_range[1] else None
            } if date_range else None
        }
        
        return {"stats": stats}
        
    except Exception as e:
        logger.error(f"Failed to get timeline stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get timeline stats: {str(e)}")