import os

from dotenv import load_dotenv
from pathlib import Path
from .zapier_manager import zapier

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Send email using Zaiper MCP
async def send_email(to, subject, body):

    return await zapier.execute(
        selected_api=os.getenv("ZAIPER_GMAIL_API"),
        action="message",
        tool_name="gmail_send_email",
        params={
            "to": [to],
            "subject": subject,
            "body": body
        }
    )


# Addend to Google SpreadSheet
async def append_sheet(spreadsheet, worksheet, values):

    return await zapier.execute(
        selected_api=os.getenv("ZAIPER_GOOGLE_SPREEDSHEET_API"),
        action="add_row",
        tool_name="google_sheets_create_spreadsheet_row",
        params={
            "spreadsheet": spreadsheet,
            "worksheet": worksheet,
            **values
        }
    )