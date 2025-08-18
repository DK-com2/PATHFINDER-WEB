from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
import pandas as pd
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

from api.auth import get_current_user
from utils.database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/data")
async def get_timeline_data(
    current_user: dict = Depends(get_current_user),
    limit: Optional[int] = 1000,
    offset: Optional[int] = 0
):
    """認証されたユーザーのタイムラインデータを取得"""
    try:
        # Get username from Supabase
        from supabase import create_client
        import os
        
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        # Get username
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            return {"message": "Username not set. Please set your username first.", "data": []}
        
        username = username_response.data[0]["username"]
        
        # Get timeline data from PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = """
            SELECT id, type, start_time, end_time, point_time, latitude, longitude,
                   visit_probability, visit_placeid, visit_semantictype,
                   activity_distancemeters, activity_type, activity_probability,
                   username, _gpx_data_source, _gpx_track_name, _gpx_elevation,
                   _gpx_speed, _gpx_point_sequence
            FROM timeline_data 
            WHERE username = %s 
            ORDER BY start_time DESC 
            LIMIT %s OFFSET %s
        """
        
        cur.execute(query, (username, limit, offset))
        rows = cur.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cur.description]
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                if isinstance(value, datetime):
                    row_dict[columns[i]] = value.isoformat()
                else:
                    row_dict[columns[i]] = value
            data.append(row_dict)
        
        cur.close()
        conn.close()
        
        return {
            "data": data,
            "count": len(data),
            "username": username,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get timeline data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get timeline data: {str(e)}")

@router.get("/summary")
async def get_timeline_summary(current_user: dict = Depends(get_current_user)):
    """認証されたユーザーのタイムラインデータサマリーを取得"""
    try:
        # Get username from Supabase
        from supabase import create_client
        import os
        
        supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        user_id = current_user["user_id"]
        
        # Get username
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            return {"message": "Username not set. Please set your username first.", "summary": {}}
        
        username = username_response.data[0]["username"]
        
        # Get summary data from PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Total count
        cur.execute("SELECT COUNT(*) FROM timeline_data WHERE username = %s", (username,))
        total_count = cur.fetchone()[0]
        
        # Type distribution
        cur.execute("""
            SELECT type, COUNT(*) as count 
            FROM timeline_data 
            WHERE username = %s 
            GROUP BY type 
            ORDER BY count DESC
        """, (username,))
        type_distribution = dict(cur.fetchall())
        
        # Date range
        cur.execute("""
            SELECT MIN(start_time) as min_date, MAX(start_time) as max_date 
            FROM timeline_data 
            WHERE username = %s AND start_time IS NOT NULL
        """, (username,))
        date_range = cur.fetchone()
        
        # Activity types
        cur.execute("""
            SELECT activity_type, COUNT(*) as count 
            FROM timeline_data 
            WHERE username = %s AND activity_type IS NOT NULL 
            GROUP BY activity_type 
            ORDER BY count DESC 
            LIMIT 10
        """, (username,))
        activity_types = dict(cur.fetchall())
        
        # Visit semantic types
        cur.execute("""
            SELECT visit_semantictype, COUNT(*) as count 
            FROM timeline_data 
            WHERE username = %s AND visit_semantictype IS NOT NULL 
            GROUP BY visit_semantictype 
            ORDER BY count DESC 
            LIMIT 10
        """, (username,))
        visit_types = dict(cur.fetchall())
        
        cur.close()
        conn.close()
        
        summary = {
            "total_records": total_count,
            "username": username,
            "type_distribution": type_distribution,
            "date_range": {
                "start": date_range[0].isoformat() if date_range[0] else None,
                "end": date_range[1].isoformat() if date_range[1] else None
            } if date_range else None,
            "top_activity_types": activity_types,
            "top_visit_types": visit_types
        }
        
        return {"summary": summary}
        
    except Exception as e:
        logger.error(f"Failed to get timeline summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get timeline summary: {str(e)}")

@router.get("/stats")
async def get_database_stats(current_user: dict = Depends(get_current_user)):
    """データベースの統計情報を取得"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Database health check
        cur.execute("SELECT 1")
        
        # Table info
        cur.execute("""
            SELECT COUNT(*) as total_records 
            FROM timeline_data
        """)
        total_records = cur.fetchone()[0]
        
        # Unique users
        cur.execute("""
            SELECT COUNT(DISTINCT username) as unique_users 
            FROM timeline_data
        """)
        unique_users = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "database_status": "healthy",
            "total_records": total_records,
            "unique_users": unique_users
        }
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")