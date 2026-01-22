from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict
import logging
import os
from supabase import create_client

from api.auth import get_current_user
from utils.database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

# Supabase Admin Client for searching users (using Service Role Key if available, else standard key)
# For user search, we ideally need list users capability which might require service role.
# However, if we can't search users table directly due to permissions, we'll assume we can search `username` table.
# Since we created a `username` table in Supabase previously (based on code analysis), we'll use that.
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@router.post("/follow/{target_username}")
async def follow_user(target_username: str, current_user: dict = Depends(get_current_user)):
    """ユーザーをフォローする"""
    try:
        # Get current username
        user_id = current_user["user_id"]
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            raise HTTPException(status_code=400, detail="Username not set")
        
        follower_username = username_response.data[0]["username"]
        
        if follower_username == target_username:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if already following
        cur.execute("""
            INSERT INTO follows (follower_username, followed_username)
            VALUES (%s, %s)
            ON CONFLICT (follower_username, followed_username) DO NOTHING
        """, (follower_username, target_username))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": f"Followed {target_username}"}
        
    except Exception as e:
        logger.error(f"Follow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unfollow/{target_username}")
async def unfollow_user(target_username: str, current_user: dict = Depends(get_current_user)):
    """ユーザーのフォローを解除する"""
    try:
        # Get current username
        user_id = current_user["user_id"]
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            raise HTTPException(status_code=400, detail="Username not set")
        
        follower_username = username_response.data[0]["username"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            DELETE FROM follows 
            WHERE follower_username = %s AND followed_username = %s
        """, (follower_username, target_username))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {"message": f"Unfollowed {target_username}"}
        
    except Exception as e:
        logger.error(f"Unfollow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{target_username}")
async def get_follow_status(target_username: str, current_user: dict = Depends(get_current_user)):
    """フォロー状態を確認する"""
    try:
        # Get current username
        user_id = current_user["user_id"]
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            return {"following": False, "followed_by": False, "mutual": False}
        
        current_username = username_response.data[0]["username"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if I follow target
        cur.execute("""
            SELECT 1 FROM follows 
            WHERE follower_username = %s AND followed_username = %s
        """, (current_username, target_username))
        following = cur.fetchone() is not None
        
        # Check if target follows me
        cur.execute("""
            SELECT 1 FROM follows 
            WHERE follower_username = %s AND followed_username = %s
        """, (target_username, current_username))
        followed_by = cur.fetchone() is not None
        
        cur.close()
        conn.close()
        
        return {
            "following": following,
            "followed_by": followed_by,
            "mutual": following and followed_by
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_users(q: str, current_user: dict = Depends(get_current_user)):
    """ユーザーを検索する"""
    try:
        if not q or len(q) < 2:
            return {"users": []}
            
        # Search username table in Supabase
        # Using ilike for case-insensitive search
        response = supabase.table("username").select("username").ilike("username", f"%{q}%").limit(10).execute()
        
        users = [{"username": u["username"]} for u in response.data]
        return {"users": users}
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/following")
async def get_following_list(current_user: dict = Depends(get_current_user)):
    """フォロー中のユーザー一覧を取得する"""
    try:
        # Get current username
        user_id = current_user["user_id"]
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        if not username_response.data:
            return {"users": []}
            
        current_username = username_response.data[0]["username"]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Determine who I follow and if they follow me back (mutual)
        # f1: I follow them (f1.follower = Me)
        # f2: They follow me (f2.follower = Them, f2.followed = Me)
        query = """
            SELECT f1.followed_username, 
                   CASE WHEN f2.follower_username IS NOT NULL THEN TRUE ELSE FALSE END as is_mutual
            FROM follows f1
            LEFT JOIN follows f2 ON f1.followed_username = f2.follower_username AND f2.followed_username = f1.follower_username
            WHERE f1.follower_username = %s
            ORDER BY f1.created_at DESC
        """
        
        cur.execute(query, (current_username,))
        rows = cur.fetchall()
        
        users = []
        for row in rows:
            users.append({
                "username": row[0],
                "mutual": row[1]
            })
            
        cur.close()
        conn.close()
        
        return {"users": users}
        
    except Exception as e:
        logger.error(f"Failed to get following list: {e}")
        raise HTTPException(status_code=500, detail=str(e))
