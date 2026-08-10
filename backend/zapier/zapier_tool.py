import json
import re
from asgiref.sync import async_to_sync
from langchain_core.tools import StructuredTool
from zapier.zapier_manager import get_zapier_manager
from zapier.zapier_config import ZAPIER_APPS_CONFIG

from common.request_context import (current_user_id, current_profile)

def normalize_email(value):
    if not value:
        return value

    value = value.strip()

    # Markdown email link:
    # [test8cs@gmail.com](mailto:test8cs@gmail.com)
    match = re.search(
        r'\[([^\]]+)\]\(mailto:([^)]+)\)',
        value,
        re.IGNORECASE
    )

    if match:
        return match.group(2).strip()

    # Plain mailto:
    # mailto:test8cs@gmail.com
    if value.lower().startswith("mailto:"):
        return value[7:].strip()

    return value

# Singleton manager
manager = get_zapier_manager()

async def _zapier_action_async(app: str, operation: str, params: dict):
    """
    Execute a Zapier action.

    Args:
        app:
            gmail
            google_sheet

        operation:
            send_email
            create_draft
            read_email
            append_row
            update_row
            etc.

        params:
            Parameters required by the Zapier action.

    
    When using zapier_action with operation="read_email":

    Use these parameters:

    sender
    recipient
    subject
    unread
    attachment

    Do NOT use:
    label

    Example

    Read my latest email from Amazon

    ↓

    {
        "app":"gmail",
        "operation":"read_email",
        "params":{
            "sender":"amazon"
        }
    }

    """

    print("=== ZAPIER ACTION ===")
    print(f"App       : {app}")
    print(f"Operation : {operation}")
    print(f"Params    : {params}")

    app = app.lower()
    operation = operation.lower()

    if app not in ZAPIER_APPS_CONFIG:
        return f"Unknown Zapier app '{app}'."

    if operation not in ZAPIER_APPS_CONFIG[app]["operations"]:
        return (
            f"Unknown operation '{operation}' "
            f"for app '{app}'."
        )

    cfg = ZAPIER_APPS_CONFIG[app]["operations"][operation]

    # print("=== ZAPIER CONFIG ===")
    # print(cfg)

    instructionsParam = f"Execute Zapier action '{cfg["action"]}'."
    outputParam = "Return success or failure with any useful details."

    # For read email : Generate new param array
    if operation == "read_email":

        original = params.copy()
        query_parts = []

        #
        # sender
        #
        sender = (original.get("sender") or original.get("from")or original.get("label"))

        if sender:
            query_parts.append(f"from:{sender}")

        #
        # recipient
        #
        if original.get("recipient"):
            query_parts.append(f'to:{original["recipient"]}')

        #
        # subject
        #
        if original.get("subject"):
            query_parts.append(f'subject:{original["subject"]}')

        #
        # unread
        #
        if original.get("unread"):
            query_parts.append("is:unread")

        #
        # attachment
        #
        if original.get("attachment"):
            query_parts.append("has:attachment")

        #
        # latest
        #
        query_parts.append("in:inbox")
        
        query = " ".join(query_parts)

        print("FINAL QUERY:", query)

        # params = {
        #     "query": query
        # }

        params = query

        instructionsParam = f"""Return the newest matching email including 
                        subject, sender, date and snippet." """
        outputParam = f"""Return only the newest matching email with 
                        "subject, from, date and snippet." """

    user_id = current_user_id.get()

    profile = current_profile.get()

    if not profile:
        return "Profile not found."

    mcp_url = profile.get("mcp_url")

    if not mcp_url:
        return "Please connect your Zapier MCP account first."


    # Normalize Gmail email addresses before sending to Zapier
    if app == "gmail" and operation in ("send_email", "create_draft", "reply_email",):
        if isinstance(params.get("to"), str):
            params["to"] = [params["to"]]

        if isinstance(params.get("to"), list):
            params["to"] = [
                normalize_email(email)
                for email in params["to"]
            ]

        if isinstance(params.get("cc"), str):
            params["cc"] = [params["cc"]]

        if isinstance(params.get("cc"), list):
            params["cc"] = [
                normalize_email(email)
                for email in params["cc"]
            ]

        if isinstance(params.get("bcc"), str):
            params["bcc"] = [params["bcc"]]

        if isinstance(params.get("bcc"), list):
            params["bcc"] = [
                normalize_email(email)
                for email in params["bcc"]
            ]

    print("NORMALIZED PARAMS:", params)


    result = await manager.execute(
        user_id=user_id,
        mcp_url=mcp_url,
        selected_api=ZAPIER_APPS_CONFIG[app]["selected_api"],
        action=cfg["action"],
        tool_name=cfg["tool_name"],
        params=params,
        instructions=instructionsParam,
        output= outputParam
    )

    print("=== ZAPIER RESULT START===")
    print(result)
    print("=== ZAPIER RESULT END===")

    # MCP returns a list of content blocks
    if isinstance(result, list) and len(result) > 0:

        text = result[0].get("text", "")

        try:
            data = json.loads(text)

            #
            # Follow-up question from Zapier
            #

            if "followUpQuestion" in data:
                return data


            if isinstance(data, dict) and data.get("results"):
            # if data.get("execution", {}).get("status") == "SUCCESS":

                result_data = {
                    "status": "SUCCESS",
                    "app": app,
                    "action": operation,
                }

                if operation in ("send_email", "create_draft", "reply_email",):
                    result_data["recipient"] = params.get("to")

                elif operation == "read_email":
                    result_data["data"] = data

                else:
                    result_data["data"] = data

                return result_data

            else:
                return f"❌ Zapier failed:\n{data.get('error')}"

        except Exception:
            return text

    return result


def _zapier_action_sync(
    app: str,
    operation: str,
    params: dict
):
    """
    Synchronous wrapper for LangGraph ToolNode.
    """
    return async_to_sync(_zapier_action_async)(
        app,
        operation,
        params
    )


zapier_action = StructuredTool.from_function(
    func=_zapier_action_sync,
    coroutine=_zapier_action_async,
    name="zapier_action",
    description="""
    Use this tool whenever the user wants to interact with Gmail,
Google Sheets, Google Docs, or other connected Zapier services.

IMPORTANT

For ALL Gmail requests ALWAYS use:

app="gmail"

--------------------------------------------------
READ EMAIL
--------------------------------------------------

Use

operation="read_email"

when the user wants to:

- read email
- check email
- search email
- latest email
- newest email
- recent email
- unread email
- inbox
- find email
- show emails

Examples

User:
Read my latest email

Tool:

app="gmail"
operation="read_email"
params={
    "max_results":1
}

----------------------------

User:
Read my latest email from Amazon

Tool:

app="gmail"
operation="read_email"
params={
    "sender":"amazon",
    "max_results":1
}

----------------------------

User:
Show unread emails

Tool:

app="gmail"
operation="read_email"
params={
    "unread":true
}

--------------------------------------------------
SEND EMAIL
--------------------------------------------------

Use

operation="send_email"

ONLY when the user wants the email to be SENT immediately.

Examples:

- send email
- email this
- mail this
- send this report
- send this weather report
- send to john@example.com
- email my manager
- forward this report
- send this message

Examples

User:
Send this weather report to test@gmail.com

Tool:

app="gmail"
operation="send_email"

----------------------------

User:
Email this report to John

Tool:

app="gmail"
operation="send_email"

IMPORTANT

If the user asks to SEND an email,
NEVER use create_draft.

--------------------------------------------------
CREATE DRAFT
--------------------------------------------------

Use

operation="create_draft"

ONLY if the user explicitly asks for a draft.

Examples:

- create draft
- save as draft
- draft an email
- prepare a draft
- compose an email
- don't send yet
- write an email draft

Example

User:
Create a draft for this report

Tool:

app="gmail"
operation="create_draft"

IMPORTANT

Draft means DO NOT SEND.

--------------------------------------------------
REPLY EMAIL
--------------------------------------------------

Use

operation="reply_email"

ONLY when the user explicitly wants to reply to an existing email.

Examples:

- reply
- reply to latest email
- respond to this email

--------------------------------------------------
GOOGLE SHEETS
--------------------------------------------------

Use

app="google_sheet"

Operations:

- append_row

--------------------------------------------------
VERY IMPORTANT
--------------------------------------------------

These operations are NEVER interchangeable.

SEND
    -> send_email

DRAFT
    -> create_draft

READ
    -> read_email

REPLY
    -> reply_email

If the user asks to SEND an email,
ALWAYS choose send_email.

Never answer Gmail questions from memory.

Never ask unnecessary clarification if enough information is already available.

Call this tool immediately.
    """,
)
