# zapier/zapier_config.py
import os

from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ZAPIER_APPS_CONFIG = {
    "gmail": {
        "selected_api": os.getenv("ZAIPER_GMAIL_API"),
        "operations": 
        {
            "send_email": {
                "action": "message",
                "tool_name": "gmail_send_email"
            },
            "create_draft": {
                "action": "draft_v2",
                "tool_name": "gmail_create_draft"
            },
            "reply_email": {
                "action": "reply_to_message",
                "tool_name": "gmail_reply_to_email"
            }
        }

    },

    "google_sheet": {
        "selected_api": os.getenv("ZAIPER_GOOGLE_SPREEDSHEET_API"),
        "operations": {
            "append_row": {
                "action": "add_row",
                "tool_name": "google_sheets_create_spreadsheet_row"
            }
        }
    }
}