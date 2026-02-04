
import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv

# Load env from .env file
load_dotenv(r"d:\Documents\pathfinder-web\.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print(f"Connecting to {SUPABASE_URL} with key (role: anon)...")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_search(query):
    print(f"Searching for '{query}'...")
    try:
        response = supabase.table("username").select("username").ilike("username", f"%{query}%").limit(10).execute()
        print("Success!")
        print(response.data)
    except Exception as e:
        print("Error encountered:")
        print(e)

if __name__ == "__main__":
    test_search("test")
