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
            append_row
            update_row
            etc.

        params:
            Parameters required by the Zapier action.
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

    print("=== ZAPIER CONFIG ===")
    print(cfg)

    result = await manager.execute(
        selected_api=ZAPIER_APPS_CONFIG[app]["selected_api"],
        action=cfg["action"],
        tool_name=cfg["tool_name"],
        params=params,
        instructions=f"Execute Zapier action '{cfg["action"]}'.",
        output= "Return success or failure with any useful details."
    )

    print("=== ZAPIER RESULT ===")
    print(result)

    # MCP returns a list of content blocks
    if isinstance(result, list) and len(result) > 0:

        text = result[0].get("text", "")

        try:
            data = json.loads(text)

            if data.get("execution", {}).get("status") == "SUCCESS":

                if app == "gmail":
                    return {
                        "status": "SUCCESS",
                        "action": "send_email",
                        "recipient": params.get("to")
                    }

                elif app == "google_sheet":
                    return {
                        "status": "SUCCESS",
                        "action": "append_row"
                    }

                elif app == "google_docs":
                    return {
                        "status": "SUCCESS",
                        "action": "update_document"
                    }

                else:
                    return {
                        "status": "SUCCESS",
                        "action": "action_completed"
                    }

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
Execute Zapier actions.

Supported Apps:
- gmail
- google_sheet
- google_docs
- google_drive

Examples:

Send Email:
app="gmail"
operation="send_email"

Create Draft:
app="gmail"
operation="create_draft"

Append Spreadsheet Row:
app="google_sheet"
operation="append_row"

Update Spreadsheet Row:
app="google_sheet"
operation="update_row"
""",
)

# # # @tool
# # # async def zapier_action(
# # #     app: str,
# # #     operation: str,
# # #     params: dict
# # # ):
# # #     """
# # #     Execute a Zapier action.

# # #     Args:
# # #         app:
# # #             gmail
# # #             google_sheet

# # #         operation:
# # #             send_email
# # #             append_row
# # #             create_draft

# # #         params:
# # #             Parameters required by the Zapier action.
# # #     """

# # #     print("ZAIPER ACTION CALLING")

# # #     app = app.lower()
# # #     operation = operation.lower()

# # #     if app not in ZAPIER_APPS_CONFIG:
# # #         return f"Unknown Zapier app '{app}'."

# # #     if operation not in ZAPIER_APPS_CONFIG[app]["operations"]:
# # #         return f"Unknown operation '{operation}'."

# # #     cfg = ZAPIER_APPS_CONFIG[app]["operations"][operation]

# # #     print("ZAIPER CONFIG : ")
# # #     print(cfg)

# # #     result = await manager.execute(
# # #         selected_api=ZAPIER_APPS_CONFIG[app]["selected_api"],
# # #         action=cfg["action"],
# # #         tool_name=cfg["tool_name"],
# # #         params=params
# # #     )

# # #     print("ZAIPER RESULT : ")
# # #     print(result)

# # #     return result