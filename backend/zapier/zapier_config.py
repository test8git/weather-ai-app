# zapier/zapier_config.py
import json
import re
import os

from dotenv import load_dotenv
from pathlib import Path

# print("========================================")
# print("LOADED ZAPIER CONFIG FROM:")
# print(__file__)
# print("========================================")

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
            },
            "read_email": {
                "action": "find",
                "tool_name": "gmail_find_email"
            }
        }
    },
    "google_docs": {
        "selected_api": os.getenv("ZAIPER_GOOGLE_DOCS_API"),

        "operations": {

            "read_document": {
                "action": "get_document_content",
                "tool_name": "google_docs_get_document_content"
            },
            "create_document": {
                "action": "create_document_from_text",
                "tool_name": "google_docs_create_document_from_text"
            },
            "append_text": {
                "action": "append_text_to_document",
                "tool_name": "google_docs_append_text_to_document"
            },
            "replace_text": {
                "action": "find_and_replace_text",
                "tool_name": "google_docs_find_and_replace_text"
            },
            "find_document": {
                "action": "find_a_document",
                "tool_name": "google_docs_find_a_document"
            },
            "share_document": {
                "action": "add_file_sharing_preference",
                "tool_name": "google_drive_add_file_sharing_preference"
            },
            "delete_document": {
                "action": "delete_file",
                "tool_name": "google_drive_delete_file"
            },

            "find_text": {
                "action": "find_text_in_document",
                "tool_name": "google_docs_find_text_in_document"
            },

            "insert_text": {
                "action": "insert_text",
                "tool_name": "google_docs_insert_text"
            }
        }
    },
    "google_sheets": {
        "selected_api": os.getenv("ZAIPER_GOOGLE_SPREEDSHEET_API"),
        "operations": {
            "find_spreadsheet": {
                "action": "find_spreadsheet",
                "tool_name": "google_sheets_find_spreadsheet"
            },
            "delete_spreadsheet": {
                "action": "delete_spreadsheet",
                "tool_name": "google_drive_delete_file"
            },
            "delete_worksheet": {
                "action": "delete_worksheet",
                "tool_name": "google_sheets_delete_sheet"
            },
            "read_spreadsheet": {
                "action": "get_spreadsheet_content",
                "tool_name": "google_sheets_get_many_spreadsheet_rows_advanced"
            },
            "delete_spreadsheet_rows": {
                "action": "delete_spreadsheet_rows",
                "tool_name": "google_sheets_delete_spreadsheet_row_s"
            },
            "create_spreadsheet": {
                "action": "create_spreadsheet",
                "tool_name": "google_sheets_create_spreadsheet"
            },
            "append_row": {
                "action": "add_row",
                "tool_name": "google_sheets_create_spreadsheet_row"
            },
            "calculate_spreadsheet": {
                "action": "calculate_spreadsheet",
                "tool_name": "google_sheets_get_many_spreadsheet_rows_advanced"
            },
            "update_row": {
                "action": "update_spreadsheet_row",
                "tool_name": "google_sheets_update_spreadsheet_row"
            },
            "share_spreadsheet": {
                "action": "share_spreadsheet",
                "tool_name": "google_drive_add_file_sharing_preference"
            },
        }
    },
    "google_calendar": {
        "operations": {

            "create_event": {
                "action": "create_event",
                "tool_name": "google_calendar_create_detailed_event"
            },
            "list_events": {
                "action": "list_events",
                "tool_name": "google_calendar_find_events"
            },
            "update_event": {
                "action": "update_event",
                "tool_name": "google_calendar_update_event"
            },
            "delete_event": {
                "action": "delete_event",
                "tool_name": "google_calendar_delete_event"
            },
        }
    }
}