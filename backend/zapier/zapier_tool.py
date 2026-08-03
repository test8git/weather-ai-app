import json
from asgiref.sync import async_to_sync
from langchain_core.tools import StructuredTool
from zapier.zapier_manager import get_zapier_manager
from zapier.zapier_config import ZAPIER_APPS_CONFIG

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

    result = await manager.execute(
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

            #
            # Gmail Find Email
            #
            if operation == "read_email":

                return {
                    "status": "SUCCESS",
                    "action": "read_email",
                    "data": data
                }

            if data.get("execution", {}).get("status") == "SUCCESS":

                if app == "gmail":

                    result_data = {
                        "status": "SUCCESS",
                        "action": operation
                    }

                    #
                    # send_email
                    #
                    if operation == "send_email":
                        result_data["recipient"] = params.get("to")

                    #
                    # create_draft
                    #
                    elif operation == "create_draft":
                        result_data["recipient"] = params.get("to")

                    #
                    # reply_email
                    #
                    elif operation == "reply_email":
                        result_data["recipient"] = params.get("to")

                    #
                    # read_email
                    #
                    elif operation == "read_email":
                        result_data["data"] = data

                    return result_data

                    # # # return {
                    # # #     "status": "SUCCESS",
                    # # #     "action": "send_email",
                    # # #     "recipient": params.get("to")
                    # # # }

                elif app == "google_sheet":
                    return {
                        "status": "SUCCESS",
                        "action": operation
                    }

                    # # # return {
                    # # #     "status": "SUCCESS",
                    # # #     "action": "append_row"
                    # # # }

                elif app == "google_docs":
                    return {
                        "status": "SUCCESS",
                        "action": operation
                    }
                    
                    # # # return {
                    # # #     "status": "SUCCESS",
                    # # #     "action": "update_document"
                    # # # }

                else:
                    return {
                        "status": "SUCCESS",
                        "action": operation,
                        "data": data
                    }

                    # # # return {
                    # # #     "status": "SUCCESS",
                    # # #     "action": "action_completed"
                    # # # }

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
        params,
    )


zapier_action = StructuredTool.from_function(
    func=_zapier_action_sync,
    coroutine=_zapier_action_async,
    name="zapier_action",
    description="""
    Use this tool whenever the user wants to interact with Gmail,
    Google Sheets, Google Docs, or other connected Zapier services.

    IMPORTANT:
    For Gmail operations, ALWAYS use app="gmail".

    Gmail operations:

    1. read_email
    Read/search Gmail messages.

    Parameters:
    - sender: sender name or email
    - recipient: recipient name or email
    - subject: subject/keyword
    - unread: true/false
    - attachment: true/false
    - max_results: number of emails to return

    Examples:

    Read latest email:
    app="gmail"
    operation="read_email"
    params={"max_results": 1}

    Read latest email from Zapier:
    app="gmail"
    operation="read_email"
    params={
        "sender": "zapier",
        "max_results": 1
    }

    Read unread emails:
    app="gmail"
    operation="read_email"
    params={
        "unread": true
    }

    2. send_email
    Send an email.

    3. create_draft
    Create an email draft.

    4. reply_email
    Reply to an email.

    Google Sheets:
    - append_row
    - update_row

    IMPORTANT:
    If the user asks to read, search, find, check, or retrieve an email,
    DO NOT answer from memory and DO NOT ask unnecessary clarification.
    Call this tool immediately when sufficient information is present.
    """,
)
