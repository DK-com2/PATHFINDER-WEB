
from supabase import create_client
import os

try:
    print(f"URL: {os.getenv('SUPABASE_URL')}")
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    print("Client created successfully with None")
    
    supabase.table("username").select("*").execute()
except Exception as e:
    print(f"Error: {e}")
