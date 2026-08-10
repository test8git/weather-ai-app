from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
import os
import re
from datetime import datetime, timezone

import httpx
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

router = APIRouter()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

async def verify_mcp_server(mcp_url: str):

    try:

        client = MultiServerMCPClient(
            {
                "zapier": {
                    "transport": "http",
                    "url": mcp_url
                }
            }
        )

        #
        # Connect to MCP
        #
        tools = await client.get_tools()

        if not tools:

            return False, "No tools returned."

        return True, tools

    except Exception as ex:

        return False, str(ex)


class MCPConnectRequest(BaseModel):
    mcp_url: str


@router.post("/connect")
async def connect_mcp(
    request: MCPConnectRequest,
    authorization: str = Header(None)
):

    if authorization is None:
        return {
            "status": False,
            "message": "Missing Authorization Header"
        }

    jwt = authorization.replace("Bearer ", "")

    #
    # Verify logged-in user
    #
    auth_user = supabase.auth.get_user(jwt)

    if auth_user.user is None:
        return {
            "status": False,
            "message": "Unauthorised Access"
        }

    user_id = auth_user.user.id

    mcp_url = request.mcp_url.strip()

    #
    # Basic validation
    #
    if not re.match(r"^https://mcp\.zapier\.com/", mcp_url ):
        return {
            "status": False,
            "message": "Invalid Zapier MCP URL"
        } 

    # verify MCP server
    ok, result = await verify_mcp_server(mcp_url)

    if not ok:
        return {
            "status": False,
            "message": f"MCP connection failed : {result}"
        }
        
    #
    # Save
    #
    supabase.table("profiles").update(
    {
        "mcp_url": mcp_url,
        "mcp_connected": True,
        "mcp_connected_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", user_id).execute()

    return {
        "status": True,
        "message": "Zapier connected successfully"
    }