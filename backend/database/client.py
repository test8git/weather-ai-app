from supabase import create_client

from dotenv import load_dotenv
from pathlib import Path

import os

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")

key = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(url, key)