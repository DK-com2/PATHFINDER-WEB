from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from typing import Optional
import os
from dotenv import load_dotenv

from models.user import UserLogin, UserResponse, Token, UserProfile
from utils.auth import create_access_token, verify_token

# 環境変数を読み込み
load_dotenv()

router = APIRouter()
security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(f"SUPABASE_URL and SUPABASE_KEY must be set. Got URL: {SUPABASE_URL}, KEY: {'***' if SUPABASE_KEY else None}")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_data = verify_token(token)
    if user_data is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_data

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user_credentials.email,
            "password": user_credentials.password
        })
        
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(
            data={"sub": response.user.id, "email": response.user.email}
        )
        
        return Token(access_token=access_token, token_type="bearer")
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Logout failed: {str(e)}")

@router.get("/verify")
async def verify_token_endpoint(current_user: dict = Depends(get_current_user)):
    return {"valid": True, "user": current_user}

@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        
        # Try to get username from the database
        username_response = supabase.table("username").select("username").eq("user_id", user_id).execute()
        username = None
        if username_response.data:
            username = username_response.data[0]["username"]
        
        return UserProfile(
            id=user_id,
            email=current_user["email"],
            username=username
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get profile: {str(e)}")

@router.post("/set-username")
async def set_username(username_data: dict, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        username = username_data.get("username")
        
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        
        # Check if username already exists for this user
        existing = supabase.table("username").select("*").eq("user_id", user_id).execute()
        
        if existing.data:
            # Update existing username
            supabase.table("username").update({"username": username}).eq("user_id", user_id).execute()
        else:
            # Insert new username
            supabase.table("username").insert({"user_id": user_id, "username": username}).execute()
        
        return {"message": "Username set successfully", "username": username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to set username: {str(e)}")