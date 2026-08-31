import json
import re
from zapier.calculation_engine import calculate_with_ai

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

def extract_zapier_json(result):

    if isinstance(result, list):

        for block in result:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                return json.loads(text)
            except Exception:
                continue

    if isinstance(result, dict):
        return result

    return None

def extract_zapier_error(result):

    if not result:
        return None

    if isinstance(result, list):

        for item in result:

            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if text:

                error = extract_zapier_error(text)

                if error:
                    return error

        return None

    if isinstance(result, str):

        try:
            data = json.loads(result)
            return extract_zapier_error(data)

        except Exception:

            if "insufficient tasks" in result.lower():
                return result

            return None

    if isinstance(result, dict):

        if result.get("isError") is True:
            return result.get("error") or "Zapier operation failed."

        if result.get("error"):
            return result["error"]

    return None

# region GOOGLE WORKSPACE COMMON HELPERS

GOOGLE_DRIVE_SHARE_TOOL = (
    "google_drive_add_file_sharing_preference"
)


GOOGLE_DRIVE_SHARE_PERMISSIONS = {
    "email",
    "public_link_edit",
    "public_link_view",
    "public_link_comment",
    "public_discoverable",
    "org_link_edit",
    "org_link_view",
    "org_link_comment",
    "org_discoverable",
}

def _google_normalize_role(role):
    """
    Normalize human-friendly sharing roles to the values
    expected by Google Drive/Zapier.
    """

    role = str(role or "").strip().lower()

    role_map = {
        "view": "reader",
        "viewer": "reader",
        "read": "reader",
        "reader": "reader",

        "edit": "writer",
        "editor": "writer",
        "write": "writer",
        "writer": "writer",

        "comment": "commenter",
        "commenter": "commenter",
    }

    return role_map.get(role, role)

def _google_parse_mcp_json(result):
    """
    Convert a Zapier/MCP result into a Python dict/list
    whenever the result contains JSON text blocks.

    Example MCP response:

        [
            {
                "type": "text",
                "text": "{\"results\": {...}}"
            }
        ]

    Returns:
        dict/list when JSON can be parsed
        original result otherwise
    """

    if result is None:
        return None

    # Already structured
    if isinstance(result, (dict, list)):
        # A list may actually be MCP content blocks.
        if isinstance(result, dict):
            return result

        for block in result:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            if isinstance(text, str):

                try:
                    parsed = json.loads(text)

                    if isinstance(
                        parsed,
                        (dict, list)
                    ):
                        return parsed

                except Exception:
                    continue

        return result

    # JSON string
    if isinstance(result, str):

        try:
            return json.loads(result)

        except Exception:
            return result

    return result

def _google_extract_result_object(result):
    """
    Extract the useful JSON result object from a Zapier/MCP
    response.

    Handles:

        {"results": {...}}

    and MCP content blocks.
    """

    data = _google_parse_mcp_json(result)

    if isinstance(data, dict):
        return data

    return data

def _google_extract_sharing_url(result):
    """
    Extract a sharing URL from a Google Drive sharing result.
    """

    data = _google_parse_mcp_json(result)

    if not data:
        return None

    # --------------------------------------------------------
    # Recursive search
    # --------------------------------------------------------

    def search(value):

        if isinstance(value, dict):

            for key in (
                "sharing_url",
                "sharingUrl",
                "url",
                "web_view_link",
                "webViewLink",
                "webContentLink",
                "alternateLink",
            ):

                candidate = value.get(key)

                if (
                    isinstance(candidate, str)
                    and candidate.strip()
                ):
                    return candidate.strip()

            for nested in value.values():

                found = search(nested)

                if found:
                    return found

        elif isinstance(value, list):

            for item in value:

                found = search(item)

                if found:
                    return found

        return None

    return search(data)

async def _google_get_drive_sharing_schema(user_id, mcp_url, permission, file_id=None):
    """
    Common dynamic-property-schema resolver for:

        google_drive_add_file_sharing_preference

    The schema depends on `permission`.
    """

    manager = get_zapier_manager()

    print("=" * 70)
    print("GOOGLE WORKSPACE SHARING SCHEMA")
    print("PERMISSION :", permission)
    print("FILE ID    :", file_id)
    print("=" * 70)

    tool_arguments = {
        "permission": permission,
        "dynamic_properties": {}
    }

    if file_id:
        tool_arguments["file_id"] = file_id

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="get_dynamic_properties_schema",
            params={
                "tool_name":
                    GOOGLE_DRIVE_SHARE_TOOL,

                "tool_arguments":
                    tool_arguments
            }
        )

        print(
            "=== GOOGLE WORKSPACE SHARING SCHEMA RESULT ==="
        )
        print(result)

        return result

    except Exception as e:

        print(
            "GOOGLE WORKSPACE SHARING SCHEMA ERROR:",
            str(e)
        )

        return None

async def _google_execute_drive_share(user_id, mcp_url, file_id, permission, dynamic_properties=None, output_hint=None):
    """
    Execute the common Google Drive sharing action.

    This is used by BOTH:

        Google Docs
        Google Sheets

    because both are Google Drive files.
    """

    manager = get_zapier_manager()

    dynamic_properties = (
        dynamic_properties
        if isinstance(
            dynamic_properties,
            dict
        )
        else {}
    )

    if not output_hint:

        output_hint = (
            "Return confirmation that the Google Workspace "
            "file was shared successfully. Include the "
            "file ID, sharing permission, recipient if "
            "applicable, and sharing URL if available."
        )

    print("=" * 70)
    print("GOOGLE WORKSPACE DRIVE SHARE")
    print("FILE ID             :", file_id)
    print("PERMISSION          :", permission)
    print("DYNAMIC PROPERTIES  :", dynamic_properties)
    print("=" * 70)

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=GOOGLE_DRIVE_SHARE_TOOL,
            params={
                "file_id": file_id,
                "permission": permission,
                "dynamic_properties":
                    dynamic_properties,
                "output_hint":
                    output_hint
            }
        )

    except Exception as e:

        print(
            "GOOGLE WORKSPACE DRIVE SHARE EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "file_id": file_id,
            "permission": permission,
            "message": (
                "Unable to share the Google Workspace file."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE WORKSPACE DRIVE SHARE RESULT ==="
    )
    print(result)

    # --------------------------------------------------------
    # Zapier error
    # --------------------------------------------------------

    error = extract_zapier_error(result)

    if error:

        return {
            "status": "ERROR",
            "file_id": file_id,
            "permission": permission,
            "message": (
                "Google Workspace file sharing failed."
            ),
            "error": error
        }

    # --------------------------------------------------------
    # Parse result
    # --------------------------------------------------------

    result_data = _google_parse_mcp_json(result)

    # Explicit MCP error
    if isinstance(result_data, dict):

        if result_data.get("isError"):

            return {
                "status": "ERROR",
                "file_id": file_id,
                "permission": permission,
                "message": (
                    "Google Workspace file sharing failed."
                ),
                "error": (
                    result_data.get("error")
                    or
                    "Google Drive sharing operation failed."
                )
            }

    # --------------------------------------------------------
    # Extract sharing URL
    # --------------------------------------------------------

    sharing_url = _google_extract_sharing_url(
        result
    )

    return {
        "status": "SUCCESS",
        "file_id": file_id,
        "permission": permission,
        "sharing_url": sharing_url,
        "data": result
    }

async def _google_build_share_dynamic_properties(user_id, mcp_url, file_id, permission, email=None, role=None, file_name=None):
    """
    Build dynamic_properties for the common Google Drive
    sharing action.

    IMPORTANT:
    We only send email-specific properties when permission
    is 'email'.

    For public/org permissions we do not invent dynamic
    properties.
    """

    permission = (
        str(permission or "")
        .strip()
        .lower()
    )

    email = (
        str(email or "")
        .strip()
    )

    role = _google_normalize_role(
        role
    )

    if permission not in GOOGLE_DRIVE_SHARE_PERMISSIONS:

        return {
            "status": "ERROR",
            "message": (
                f"Unsupported sharing permission "
                f"'{permission}'."
            )
        }

    if permission == "email" and not email:

        return {
            "status": "ERROR",
            "message": (
                "An email address is required when "
                "permission='email'."
            )
        }

    # --------------------------------------------------------
    # IMPORTANT
    #
    # Call schema resolver BEFORE constructing dynamic props.
    # --------------------------------------------------------

    schema_result = (
        await _google_get_drive_sharing_schema(
            user_id=user_id,
            mcp_url=mcp_url,
            permission=permission,
            file_id=file_id
        )
    )

    if not schema_result:

        return {
            "status": "ERROR",
            "message": (
                "Unable to determine the dynamic sharing "
                "properties from Zapier."
            )
        }

    dynamic_properties = {}

    # --------------------------------------------------------
    # Email sharing
    # --------------------------------------------------------

    if permission == "email":

        dynamic_properties["email"] = email

        if role in {
            "reader",
            "writer",
            "commenter"
        }:

            dynamic_properties["role"] = role

        dynamic_properties[
            "sendNotificationEmail"
        ] = True

        dynamic_properties[
            "emailMessage"
        ] = (
            "The Google Workspace file"
            + (
                f" '{file_name}'"
                if file_name
                else ""
            )
            + " has been shared with you."
        )

    return {
        "status": "SUCCESS",
        "dynamic_properties":
            dynamic_properties,
        "schema":
            schema_result
    }

# endregion


# region Google Docs related helper functions

async def _resolve_google_doc_id(user_id, mcp_url, document_name=None, document_id=None, tool_name="google_docs_find_a_document", enum_property_name="file"):
    """
    Resolve a Google Doc ID.

    Priority:
        1. Explicit document_id
        2. Google Docs find-by-name
        3. Zapier dynamic enum fallback

    Returns:
        Google Doc ID string, or None if not found.
    """

    manager = get_zapier_manager()

    document_id = (document_id or "").strip()
    document_name = (document_name or "").strip()

    # ============================================================
    # STEP 1: Explicit document ID
    # ============================================================

    if document_id:
        print(
            f"GOOGLE DOC RESOLVE: using supplied "
            f"document_id={document_id}"
        )

        return document_id

    if not document_name:
        print(
            "GOOGLE DOC RESOLVE: no document_name or document_id"
        )

        return None

    # ============================================================
    # STEP 2: Find Google Doc by name
    # ============================================================

    print(
        f"GOOGLE DOC RESOLVE: finding document "
        f"by name='{document_name}'"
    )

    try:

        find_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_docs_find_a_document",
            params={
                "title": document_name,
                "output_hint": (
                    "Return the document ID and title."
                )
            }
        )

        print("=== GOOGLE DOC FIND RESULT ===")
        print(find_result)
        print("=== END GOOGLE DOC FIND RESULT ===")

        resolved_id = extract_google_doc_id(
            find_result
        )

        if resolved_id:

            print(
                f"GOOGLE DOC RESOLVE: found ID="
                f"{resolved_id}"
            )

            return resolved_id

    except Exception as e:

        print(
            f"GOOGLE DOC FIND ERROR: {e}"
        )

    # ============================================================
    # STEP 3: Dynamic enum fallback
    # ============================================================

    print(
        "=== GOOGLE DOC RESOLVE: USING DYNAMIC ENUM ==="
    )

    try:

        enum_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="list_dynamic_enum_values",
            params={
                "tool_name": tool_name,
                "property_name": enum_property_name,
                "search": document_name
            }
        )

        print("=== GOOGLE DOC ENUM RESULT ===")
        print(enum_result)
        print("=== END GOOGLE DOC ENUM RESULT ===")

        resolved_id = extract_google_doc_enum_value(
            enum_result,
            document_name
        )

        if resolved_id:

            print(
                f"GOOGLE DOC RESOLVE: enum found ID="
                f"{resolved_id}"
            )

            return resolved_id

    except Exception as e:

        print(
            f"GOOGLE DOC ENUM ERROR: {e}"
        )

    # ============================================================
    # STEP 4: Not found
    # ============================================================

    print(
        f"GOOGLE DOC RESOLVE: "
        f"'{document_name}' not found"
    )

    return None

def extract_google_doc_id(result):

    if not result:
        return None

    # ============================================================
    # String
    # ============================================================

    if isinstance(result, str):

        # Try JSON
        try:
            data = json.loads(result)

            found = extract_google_doc_id(data)

            if found:
                return found

        except Exception:
            pass

        # Only accept known Google document ID fields.
        patterns = [
            r'"document_id"\s*:\s*"([^"]+)"',
            r'"documentId"\s*:\s*"([^"]+)"',
            r'"file_id"\s*:\s*"([^"]+)"',
            r'"fileId"\s*:\s*"([^"]+)"',
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                result,
                re.IGNORECASE
            )

            if match:
                return match.group(1).strip()

        return None

    # ============================================================
    # List
    # ============================================================

    if isinstance(result, list):

        for item in result:

            if not isinstance(item, dict):
                continue

            # IMPORTANT:
            # MCP content block has its own "id":
            #
            # {
            #   "type": "text",
            #   "text": "...",
            #   "id": "lc_xxxxx"
            # }
            #
            # NEVER treat this id as Google Doc ID.

            text = item.get("text")

            if text:

                found = extract_google_doc_id(text)

                if found:
                    return found

            # Search other known fields, but NOT generic "id"
            for key in (
                "document_id",
                "documentId",
                "file_id",
                "fileId",
                "value",
            ):

                value = item.get(key)

                if isinstance(value, str) and value.strip():

                    return value.strip()

        return None

    # ============================================================
    # Dictionary
    # ============================================================

    if isinstance(result, dict):

        # First: known Google document ID fields
        for key in (
            "document_id",
            "documentId",
            "file_id",
            "fileId",
        ):

            value = result.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        # Dynamic enum:
        #
        # {
        #     "value": "1ppoq0...",
        #     "label": "Sales Report"
        # }
        #
        value = result.get("value")

        if isinstance(value, str) and value.strip():

            # Only accept it when it looks like a Google document ID.
            # Google Docs IDs normally do NOT start with "lc_".
            if not value.startswith("lc_"):
                return value.strip()

        # Search nested structures
        for key, value in result.items():

            # NEVER recursively treat a generic "id" as a document ID
            if key == "id":
                continue

            found = extract_google_doc_id(value)

            if found:
                return found

    return None

def extract_google_doc_enum_value(result, document_name=None):
    """
    Extract the Zapier dynamic-enum value for a Google Doc.

    Dynamic enum response:

    {
        "values": [
            {
                "value": "1abc...",
                "label": "Sales Report"
            }
        ]
    }

    Returns the `value` whose label matches document_name.
    """

    if not result:
        return None

    data = result

    # ------------------------------------------------------------
    # MCP content block
    # ------------------------------------------------------------

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                data = json.loads(text)
                break
            except Exception:
                continue

    # ------------------------------------------------------------
    # JSON object
    # ------------------------------------------------------------

    if not isinstance(data, dict):
        return None

    values = data.get("values")

    if not isinstance(values, list):
        return None

    # ------------------------------------------------------------
    # Find exact label match
    # ------------------------------------------------------------

    if document_name:

        wanted = document_name.strip().casefold()

        for item in values:

            if not isinstance(item, dict):
                continue

            label = str(
                item.get("label") or ""
            ).strip()

            value = item.get("value")

            if (
                label.casefold() == wanted
                and isinstance(value, str)
                and value.strip()
            ):
                return value.strip()

    # ------------------------------------------------------------
    # No exact match
    # ------------------------------------------------------------

    return None

def extract_google_doc_url(result):

    if not result:
        return None

    if isinstance(result, str):

        try:
            data = json.loads(result)
            found = extract_google_doc_url(data)

            if found:
                return found

        except Exception:
            pass

        match = re.search(
            r'"(?:document_url|web_url|alternateLink)"\s*:\s*"([^"]+)"',
            result,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

        return None

    if isinstance(result, list):

        for item in result:

            found = extract_google_doc_url(item)

            if found:
                return found

        return None

    if isinstance(result, dict):

        for key in (
            "document_url",
            "web_url",
            "alternateLink",
        ):

            value = result.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        for key, value in result.items():

            if key == "id":
                continue

            found = extract_google_doc_url(value)

            if found:
                return found

    return None

def extract_google_doc_content(result):
    """
    Convert the Zapier/MCP Google Docs response into
    a simple application-level structure.

    Returns:

    {
        "title": "...",
        "text_content": "..."
    }
    """

    if not result:
        return {
            "title": "",
            "text_content": "",
        }

    data = result

    # --------------------------------------------------
    # MCP content block
    # --------------------------------------------------

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                data = json.loads(text)
                break

            except Exception:
                # Not JSON; keep raw text
                data = text
                break

    # --------------------------------------------------
    # Zapier response
    #
    # {
    #   "results": {
    #       "title": "...",
    #       "text_content": "..."
    #   }
    # }
    # --------------------------------------------------

    if isinstance(data, dict):

        results = data.get("results")

        if isinstance(results, dict):

            return {
                "title": (
                    results.get("title")
                    or ""
                ),
                "text_content": (
                    results.get("text_content")
                    or ""
                ),
            }

        # fallback
        return {
            "title": data.get("title", ""),
            "text_content": (
                data.get("text_content")
                or data.get("content")
                or data.get("text")
                or ""
            ),
        }

    # --------------------------------------------------
    # Plain text fallback
    # --------------------------------------------------

    if isinstance(data, str):

        return {
            "title": "",
            "text_content": data,
        }

    return {
        "title": "",
        "text_content": str(data),
    }

async def _find_google_doc(user_id, mcp_url, params):

    manager = get_zapier_manager()

    document_name = (
        params.get("document_name")
        or params.get("title")
        or ""
    ).strip()

    print("=" * 50)
    print("GOOGLE DOC FIND")
    print(f"DOCUMENT NAME: {document_name}")
    print("=" * 50)

    if not document_name:
        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "find_document",
            "message": (
                "Please provide a document_name."
            )
        }

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_docs_find_a_document",
            params={
                "title": document_name,
                "output_hint": (
                    "Return the matching Google Doc "
                    "document ID and title. "
                    "Return only the document ID and title."
                )
            }
        )

        print("=== GOOGLE DOC FIND RAW RESULT ===")
        print(result)
        print("=== END GOOGLE DOC FIND RAW RESULT ===")

        # --------------------------------------------------------
        # Check Zapier error
        # --------------------------------------------------------

        error = extract_zapier_error(result)

        if error:

            print(
                f"=== GOOGLE DOC FIND ERROR === {error}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "find_document",
                "document_name": document_name,
                "message": (
                    "Unable to search for the Google Doc."
                ),
                "error": error
            }

        # --------------------------------------------------------
        # Extract document ID
        # --------------------------------------------------------

        document_id = extract_google_doc_id(
            result
        )

        print(
            f"GOOGLE DOC RESOLVED ID: {document_id}"
        )

        if not document_id:

            return {
                "status": "NOT_FOUND",
                "app": "google_docs",
                "action": "find_document",
                "document_name": document_name,
                "message": (
                    f"Google Doc '{document_name}' "
                    "was not found."
                )
            }

        # --------------------------------------------------------
        # Extract URL if available
        # --------------------------------------------------------

        document_url = extract_google_doc_url(
            result
        )

        return {
            "status": "SUCCESS",
            "app": "google_docs",
            "action": "find_document",
            "document_name": document_name,
            "document_id": document_id,
            "document_url": document_url,
            "message": (
                f"Google Doc '{document_name}' "
                "was found successfully."
            )
        }

    except Exception as e:

        print(
            f"GOOGLE DOC FIND ERROR: {e}"
        )

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "find_document",
            "document_name": document_name,
            "message": (
                "Unable to find the Google Doc."
            ),
            "error": str(e)
        }

async def _read_google_doc(user_id, mcp_url, params):

    manager = get_zapier_manager()

    document_id = (params.get("document_id") or "").strip()
    document_name = (params.get("document_name") or "").strip()

    if document_id:

        print(
            f"GOOGLE DOC READ: using document_id={document_id}"
        )

        try:

            result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name="google_docs_get_document_content",
                params={
                    "document_id": document_id,
                    "output_hint": (
                        "Return the complete text content of the Google Doc and its title. Do not return unnecessary metadata."
                    )
                }
            )

            doc = extract_google_doc_content(result)

            print("=== NORMALIZED GOOGLE DOC ===")
            print(doc)

            return {
                "status": "SUCCESS",
                "app": "google_docs",
                "action": "read_document",
                "document_id": document_id,
                "document_name": (
                    doc["title"]
                    or document_name
                ),
                "data": doc["text_content"],
            }

        except Exception as e:

            print(
                f"GOOGLE DOC READ ERROR: {e}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "read_document",
                "message": "Unable to read the Google Doc.",
                "error": str(e),
            }

    # ============================================================
    # CASE 2: document_name supplied
    # ============================================================

    if document_name:

        print(
            f"GOOGLE DOC READ: finding document "
            f"by name='{document_name}'"
        )

        try:

            find_result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name="google_docs_find_a_document",
                params={
                    "title": document_name,
                    "output_hint": (
                        "Return the document ID and title of "
                        "the matching Google Doc."
                    )
                }
            )

            print("=== GOOGLE DOC FIND RESULT ===")
            print(find_result)
            print("=== END GOOGLE DOC FIND RESULT ===")

        except Exception as e:

            print(
                f"GOOGLE DOC FIND ERROR: {e}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "read_document",
                "message": (
                    f"Unable to find Google Doc "
                    f"'{document_name}'."
                ),
                "error": str(e),
            }

        # --------------------------------------------------------
        # Extract document ID
        # --------------------------------------------------------

        document_id = extract_google_doc_id(
            find_result
        )

        print(
            f"GOOGLE DOC RESOLVED ID: {document_id}"
        )

        if not document_id:

            return {
                "status": "NOT_FOUND",
                "app": "google_docs",
                "action": "read_document",
                "message": (
                    f"Google Doc '{document_name}' "
                    "could not be found."
                )
            }

        # --------------------------------------------------------
        # Retrieve actual document content
        # --------------------------------------------------------

        print(
            f"GOOGLE DOC READ: retrieving content "
            f"for document_id={document_id}"
        )

        try:

            result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name="google_docs_get_document_content",
                params={
                    "document_id": document_id,
                    "output_hint": (
                        "Return the complete text content of the Google Doc and its title. Do not return unnecessary metadata."
                    )
                }
            )

            print(
                "=== GOOGLE DOC CONTENT RETRIEVED ==="
            )

            doc = extract_google_doc_content(result)

            return {
                "status": "SUCCESS",
                "app": "google_docs",
                "action": "read_document",
                "document_id": document_id,
                "document_name": (
                    doc["title"]
                    or document_name
                ),
                "data": doc["text_content"],
            }

        except Exception as e:

            print(
                f"GOOGLE DOC READ ERROR: {e}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "read_document",
                "document_id": document_id,
                "message": "Unable to read the Google Doc.",
                "error": str(e),
            }

    # ============================================================
    # CASE 3: Nothing supplied
    # ============================================================

    return {
        "status": "ERROR",
        "app": "google_docs",
        "action": "read_document",
        "message": (
            "Please provide either document_name "
            "or document_id."
        )
    }

def extract_google_doc_create_result(result):
    """
    Extract created Google Doc information from Zapier/MCP result.

    Returns:
    {
        "title": "...",
        "document_id": "...",
        "document_url": "...",
        "web_url": "..."
    }
    """

    if not result:
        return {}

    data = result

    # MCP content blocks
    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                data = json.loads(text)
                break

            except Exception:
                continue

    if not isinstance(data, dict):
        return {}

    # Zapier wraps result in "results"
    results = data.get("results")

    if isinstance(results, dict):
        data = results

    return {
        "title": data.get("title") or "",
        "document_id": (
            data.get("document_id")
            or data.get("documentId")
            or data.get("file_id")
            or ""
        ),
        "document_url": (
            data.get("document_url")
            or data.get("web_url")
            or ""
        ),
        "web_url": (
            data.get("web_url")
            or data.get("document_url")
            or ""
        ),
    }

async def _create_google_doc(user_id, mcp_url, params):

    manager = get_zapier_manager()

    title = (params.get("title") or "").strip()

    # IMPORTANT:
    # Your AI currently sends "content", but Zapier expects "file".
    content = params.get("content") or ""

    if not title:
        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "create_document",
            "message": "Please provide a document title."
        }

    print("================================================")
    print("GOOGLE DOC CREATE")
    print(f"TITLE   : {title}")
    print(f"CONTENT : {content}")
    print("================================================")

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_docs_create_document_from_text",
            params={
                "title": title,

                # Zapier MCP expects "file"
                "file": content,

                "output_hint": (
                    "Return only the newly created Google Doc "
                    "title, document_id, document_url, web_url "
                    "and file_id."
                )
            }
        )

        print("")
        print("=== GOOGLE DOC CREATE RAW RESULT ===")
        print(result)
        print("=== END RAW RESULT ===")
        print("")

        # --------------------------------------------------
        # Normalize result
        # --------------------------------------------------

        doc = extract_google_doc_create_result(result)

        print("=== NORMALIZED GOOGLE DOC CREATE RESULT ===")
        print(doc)
        print("=== END NORMALIZED RESULT ===")

        if not doc.get("document_id"):

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "create_document",
                "message": (
                    "Google Doc creation completed, "
                    "but no document ID was returned."
                ),
                "raw_result": result
            }

        return {
            "status": "SUCCESS",
            "app": "google_docs",
            "action": "create_document",
            "message": "Google Doc created successfully.",
            "document_name": doc.get("title") or title,
            "document_id": doc["document_id"],
            "document_url": (doc.get("document_url") or doc.get("web_url") or ""),
            "data": {
                "title": doc.get("title") or title,
                "document_id": doc["document_id"],
                "document_url": (doc.get("document_url") or doc.get("web_url") or "")
            }
        }

    except Exception as e:

        print("")
        print("=== GOOGLE DOC CREATE ERROR ===")
        print(e)
        print("=== END GOOGLE DOC CREATE ERROR ===")
        print("")

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "create_document",
            "document_name": title,
            "message": "Unable to create the Google Doc.",
            "error": str(e)
        }

async def _append_google_doc(user_id, mcp_url, params):

    manager = get_zapier_manager()

    document_id = (params.get("document_id") or "").strip()
    document_name = (params.get("document_name") or params.get("file") or "").strip()

    content = (params.get("content") or params.get("text") or "")

    if not document_name and not document_id:
        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "append_text",
            "message": (
                "Please provide document_name "
                "or document_id."
            )
        }

    # ============================================================
    # STEP 1: Resolve Google Doc ID
    # ============================================================

    document_id = await _resolve_google_doc_id(
        user_id=user_id,
        mcp_url=mcp_url,
        document_name=document_name,
        document_id=document_id,
        tool_name="google_docs_append_text_to_document",
        enum_property_name="file"
    )

    print(
        f"GOOGLE DOC RESOLVED ID: {document_id}"
    )

    # ------------------------------------------------------------
    # STEP 2: Document does NOT exist -> CREATE
    # ------------------------------------------------------------

    if not document_id:

        print(
            f"GOOGLE DOC DOES NOT EXIST: "
            f"creating '{document_name}'"
        )

        try:

            create_result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name="google_docs_create_document_from_text",
                params={
                    "title": document_name,
                    "file": content,
                    "output_hint": (
                        "Return the newly created Google Doc "
                        "title, document_id and document_url."
                    )
                }
            )

            print("=== GOOGLE DOC CREATE RESULT ===")
            print(create_result)

            doc = extract_google_doc_create_result(
                create_result
            )

            document_id = doc.get("document_id")

            if not document_id:
                return {
                    "status": "ERROR",
                    "app": "google_docs",
                    "action": "create_document",
                    "document_name": document_name,
                    "message": (
                        "Document was created, but no "
                        "document ID was returned."
                    ),
                    "data": create_result
                }

            document_url = (
                doc.get("document_url")
                or doc.get("web_url")
                or ""
            )

            # IMPORTANT:
            # Creation already included the content.
            # Therefore DO NOT append again.
            return {
                "status": "SUCCESS",
                "app": "google_docs",
                "action": "create_document",
                "document_name": (
                    doc.get("title")
                    or document_name
                ),
                "document_id": document_id,
                "document_url": document_url,
                "message": (
                    f"Google Doc '{document_name}' "
                    "did not exist, so it was created "
                    "with the requested content."
                )
            }

        except Exception as e:

            print(
                f"GOOGLE DOC CREATE ERROR: {e}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "create_document",
                "document_name": document_name,
                "message": (
                    f"Unable to create Google Doc "
                    f"'{document_name}'."
                ),
                "error": str(e)
            }

    # ------------------------------------------------------------
    # STEP 3: Existing document -> APPEND
    # ------------------------------------------------------------

    print(
        f"GOOGLE DOC EXISTS: "
        f"document_id={document_id}"
    )

    try:

        append_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_docs_append_text_to_document",
            params={
                "file": document_id,
                "text": content,
                "newline": True,
                "output_hint": (
                    "Return confirmation that the text "
                    "was appended successfully."
                )
            }
        )

        print("=== GOOGLE DOC APPEND RESULT ===")
        print(append_result)

        error = extract_zapier_error(
            append_result
        )

        if error:

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "append_text",
                "document_name": document_name,
                "document_id": document_id,
                "message": (
                    "Google Doc was found, but the "
                    "content could not be appended."
                ),
                "error": error
            }

        return {
            "status": "SUCCESS",
            "app": "google_docs",
            "action": "append_text",
            "document_name": document_name,
            "document_id": document_id,
            "message": (
                f"Content successfully appended "
                f"to '{document_name}'."
            )
        }

    except Exception as e:

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "append_text",
            "document_name": document_name,
            "document_id": document_id,
            "message": (
                "Unable to append content to "
                "the Google Doc."
            ),
            "error": str(e)
        }

async def _replace_google_doc(user_id, mcp_url, params):

    manager = get_zapier_manager()

    document_id = (
        params.get("document_id") or ""
    ).strip()

    document_name = (
        params.get("document_name") or ""
    ).strip()

    find_text = (
        params.get("find_text") or ""
    )

    replace_text = (
        params.get("replace_text") or ""
    )

    match_case = params.get(
        "match_case",
        False
    )

    print("=" * 50)
    print("GOOGLE DOC FIND AND REPLACE")
    print(f"DOCUMENT NAME : {document_name}")
    print(f"DOCUMENT ID   : {document_id}")
    print(f"FIND TEXT     : {find_text}")
    print(f"REPLACE TEXT  : {replace_text}")
    print(f"MATCH CASE    : {match_case}")
    print("=" * 50)

    # ============================================================
    # Validate
    # ============================================================

    if not document_id and not document_name:
        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "replace_text",
            "message": (
                "Please provide document_name or document_id."
            )
        }

    if not find_text:
        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "replace_text",
            "message": (
                "Please provide find_text."
            )
        }

    # ============================================================
    # STEP 1: Resolve Google Doc ID
    # ============================================================

    document_id = await _resolve_google_doc_id(
        user_id=user_id,
        mcp_url=mcp_url,
        document_name=document_name,
        document_id=document_id,
        tool_name="google_docs_find_and_replace_text",
        enum_property_name="document_id"
    )

    print(
        f"GOOGLE DOC REPLACE RESOLVED ID: "
        f"{document_id}"
    )

    # ============================================================
    # STEP 2
    # Document not found
    # ============================================================

    if not document_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_docs",
            "action": "replace_text",
            "document_name": document_name,
            "message": (
                f"Google Doc '{document_name}' "
                "could not be found."
            )
        }

    # ============================================================
    # STEP 3
    # Find and replace
    # ============================================================

    print(
        f"GOOGLE DOC REPLACE: document_id={document_id}"
    )

    try:

        replace_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_docs_find_and_replace_text",
            params={
                "document_id": document_id,
                "find_text": find_text,
                "replace_text": replace_text,
                "match_case": match_case,
                "output_hint": (
                    "Return confirmation that the text "
                    "was successfully replaced, including "
                    "the document ID and replacement details."
                )
            }
        )

        print(
            "=== GOOGLE DOC REPLACE RAW RESULT ==="
        )
        print(replace_result)
        print(
            "=== END GOOGLE DOC REPLACE RAW RESULT ==="
        )

        # ========================================================
        # Check Zapier error
        # ========================================================

        error = extract_zapier_error(
            replace_result
        )

        if error:

            print(
                f"=== GOOGLE DOC REPLACE ERROR === "
                f"{error}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "replace_text",
                "document_name": document_name,
                "document_id": document_id,
                "message": (
                    "Google Doc was found, but "
                    "the text could not be replaced."
                ),
                "error": error
            }

        return {
            "status": "SUCCESS",
            "app": "google_docs",
            "action": "replace_text",
            "document_name": document_name,
            "document_id": document_id,
            "message": (
                f"Successfully replaced "
                f"'{find_text}' with "
                f"'{replace_text}'."
            ),
            "data": replace_result
        }

    except Exception as e:

        print(
            f"GOOGLE DOC REPLACE ERROR: {e}"
        )

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "replace_text",
            "document_name": document_name,
            "document_id": document_id,
            "message": (
                "Unable to replace text "
                "in the Google Doc."
            ),
            "error": str(e)
        }

async def _share_google_doc(user_id, mcp_url, params):
    """
    Share a Google Doc.

    The actual sharing operation is delegated to the
    common Google Workspace / Google Drive helper.
    """

    document_name = (
        params.get("document_name")
        or params.get("file")
        or ""
    ).strip()

    document_id = (
        params.get("document_id")
        or ""
    ).strip()

    email = (
        params.get("email")
        or ""
    ).strip()

    permission = (
        params.get("permission")
        or "email"
    ).strip()

    role = (
        params.get("role")
        or ""
    ).strip()

    print("=" * 70)
    print("GOOGLE DOC SHARE")
    print("DOCUMENT NAME :", document_name)
    print("DOCUMENT ID   :", document_id)
    print("EMAIL         :", email)
    print("PERMISSION    :", permission)
    print("ROLE          :", role)
    print("=" * 70)

    # ========================================================
    # Resolve document ID
    # ========================================================

    if not document_id:

        document_id = await _resolve_google_doc_id(
            user_id=user_id,
            mcp_url=mcp_url,
            document_name=document_name,
            document_id=None,
            tool_name=(
                GOOGLE_DRIVE_SHARE_TOOL
            ),
            enum_property_name="file"
        )

    if not document_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_docs",
            "action": "share_document",
            "document_name": document_name,
            "message": (
                f"Google Doc '{document_name}' "
                "could not be found."
            )
        }

    # ========================================================
    # Build dynamic properties
    # ========================================================

    props_result = (
        await _google_build_share_dynamic_properties(
            user_id=user_id,
            mcp_url=mcp_url,
            file_id=document_id,
            permission=permission,
            email=email,
            role=role,
            file_name=document_name
        )
    )

    if props_result.get("status") != "SUCCESS":

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "share_document",
            "document_name": document_name,
            "document_id": document_id,
            "message": props_result.get(
                "message",
                "Unable to prepare sharing request."
            )
        }

    # ========================================================
    # Execute common Drive share
    # ========================================================

    share_result = (
        await _google_execute_drive_share(
            user_id=user_id,
            mcp_url=mcp_url,
            file_id=document_id,
            permission=permission,
            dynamic_properties=(
                props_result[
                    "dynamic_properties"
                ]
            ),
            output_hint=(
                "Return confirmation that the Google "
                "document was shared successfully, "
                "including document ID, permission, "
                "recipient if applicable, and sharing "
                "URL if available."
            )
        )
    )

    if share_result.get("status") != "SUCCESS":

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "share_document",
            "document_name": document_name,
            "document_id": document_id,
            "permission": permission,
            "message": (
                "Google Doc sharing failed."
            ),
            "error": share_result.get("error")
        }

    response = {
        "status": "SUCCESS",
        "app": "google_docs",
        "action": "share_document",
        "document_name": document_name,
        "document_id": document_id,
        "permission": permission,
        "email": email or None,
        "message": (
            f"Google Doc '{document_name}' "
            "was shared successfully."
        )
    }

    if share_result.get("sharing_url"):

        response["sharing_url"] = (
            share_result["sharing_url"]
        )

    return response

async def _delete_google_doc(user_id, mcp_url, params):

    manager = get_zapier_manager()

    document_id = (params.get("document_id") or "").strip()

    document_name = (params.get("document_name") or "").strip()

    print("=" * 60)
    print("GOOGLE DOC DELETE")
    print(f"DOCUMENT NAME : {document_name}")
    print(f"DOCUMENT ID   : {document_id}")
    print("=" * 60)

    # ------------------------------------------------------------
    # Validate input
    # ------------------------------------------------------------

    if not document_id and not document_name:

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "delete_document",
            "message": (
                "Please provide document_name "
                "or document_id."
            )
        }

    # ------------------------------------------------------------
    # Resolve document ID
    # ------------------------------------------------------------

    if not document_id:

        print(
            f"GOOGLE DOC DELETE: resolving "
            f"document name='{document_name}'"
        )

        document_id = await _resolve_google_doc_id(
            user_id=user_id,
            mcp_url=mcp_url,
            document_name=document_name,
            document_id=None,
            tool_name="google_drive_delete_file",
            enum_property_name="fileId"
        )

        print(
            f"GOOGLE DOC DELETE: resolved ID="
            f"{document_id}"
        )

    # ------------------------------------------------------------
    # Document not found
    # ------------------------------------------------------------

    if not document_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_docs",
            "action": "delete_document",
            "document_name": document_name,
            "message": (
                f"Google Doc '{document_name}' "
                "could not be found."
            )
        }

    # ------------------------------------------------------------
    # Delete Google Drive file
    # ------------------------------------------------------------

    print(
        "GOOGLE DOC DELETE: calling "
        "google_drive_delete_file"
    )

    try:

        delete_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_drive_delete_file",
            params={
                "fileId": document_id,
                "output_hint": (
                    "Return confirmation that the "
                    "Google Drive file was deleted "
                    "successfully, including its file ID."
                )
            }
        )

        print(
            "=== GOOGLE DOC DELETE RAW RESULT ==="
        )
        print(delete_result)
        print(
            "=== END GOOGLE DOC DELETE RESULT ==="
        )

        # --------------------------------------------------------
        # Check Zapier error
        # --------------------------------------------------------

        error = extract_zapier_error(
            delete_result
        )

        if error:

            print(
                f"=== GOOGLE DOC DELETE ERROR === "
                f"{error}"
            )

            return {
                "status": "ERROR",
                "app": "google_docs",
                "action": "delete_document",
                "document_name": document_name,
                "document_id": document_id,
                "message": (
                    "Google Doc could not be deleted."
                ),
                "error": error
            }

        return {
            "status": "SUCCESS",
            "app": "google_docs",
            "action": "delete_document",
            "document_name": document_name,
            "document_id": document_id,
            "message": (
                f"Google Doc '{document_name}' "
                "was deleted successfully."
            )
        }

    except Exception as e:

        print(
            f"GOOGLE DOC DELETE EXCEPTION: {e}"
        )

        return {
            "status": "ERROR",
            "app": "google_docs",
            "action": "delete_document",
            "document_name": document_name,
            "document_id": document_id,
            "message": (
                "Unable to delete the Google Doc."
            ),
            "error": str(e)
        }

# endregion


# region Google Sheets related helper functions


async def _resolve_google_spreadsheet_id(user_id, mcp_url, spreadsheet_id=None, spreadsheet_name=None, tool_name="google_sheets_find_spreadsheet", enum_property_name="spreadsheet_id"):
    """
    Resolve a Google Spreadsheet ID.

    Resolution order:

    1. If spreadsheet_id is supplied -> use it directly.
    2. Otherwise search spreadsheet by name.
    3. If normal search does not return an ID,
       use the dynamic enum of the requested Sheets tool.
    4. Return None if the spreadsheet cannot be resolved.
    """

    manager = get_zapier_manager()

    spreadsheet_id = (spreadsheet_id or "").strip()

    spreadsheet_name = (spreadsheet_name or "").strip()

    # ============================================================
    # STEP 1
    # Spreadsheet ID already supplied
    # ============================================================

    if spreadsheet_id:

        print(
            f"GOOGLE SHEETS RESOLVE: "
            f"using supplied spreadsheet_id={spreadsheet_id}"
        )

        return spreadsheet_id

    # ============================================================
    # STEP 2
    # Spreadsheet name required
    # ============================================================

    if not spreadsheet_name:

        print(
            "GOOGLE SHEETS RESOLVE: "
            "no spreadsheet_id or spreadsheet_name supplied"
        )

        return None

    print(
        f"GOOGLE SHEETS RESOLVE: "
        f"finding spreadsheet by name='{spreadsheet_name}'"
    )

    # ============================================================
    # STEP 3
    # Try Google Sheets search/find tool
    # ============================================================

    try:

        find_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_sheets_find_spreadsheet",
            params={
                "title": spreadsheet_name,
                "output_hint": (
                    "Return the spreadsheet ID and spreadsheet name "
                    "of the matching Google Spreadsheet."
                )
            }
        )

        print(
            "=== GOOGLE SHEETS FIND RESULT ==="
        )
        print(find_result)
        print(
            "=== END GOOGLE SHEETS FIND RESULT ==="
        )

        spreadsheet_id = extract_google_spreadsheet_id(
            find_result
        )

        if spreadsheet_id:

            print(
                f"GOOGLE SHEETS RESOLVE: "
                f"found ID={spreadsheet_id}"
            )

            return spreadsheet_id

    except Exception as e:

        print(
            f"GOOGLE SHEETS FIND ERROR: {e}"
        )

    # ============================================================
    # STEP 4
    # Dynamic enum fallback
    # ============================================================

    print(
        "=== GOOGLE SHEETS DYNAMIC ENUM FALLBACK ==="
    )

    try:

        enum_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="list_dynamic_enum_values",
            params={
                # IMPORTANT:
                # Change this tool name to the actual Sheets
                # operation that owns the spreadsheet selector.
                "tool_name":tool_name,
                # Change this if the actual property is different.
                "property_name": enum_property_name,

                "search": spreadsheet_name
            }
        )

        print(
            "=== GOOGLE SHEETS ENUM RESULT ==="
        )
        print(enum_result)
        print(
            "=== END GOOGLE SHEETS ENUM RESULT ==="
        )

        spreadsheet_id = extract_google_spreadsheet_enum_value(
            enum_result,
            spreadsheet_name
        )

        if spreadsheet_id:

            print(
                f"GOOGLE SHEETS RESOLVE: "
                f"dynamic enum returned ID="
                f"{spreadsheet_id}"
            )

            return spreadsheet_id

    except Exception as e:

        print(
            f"GOOGLE SHEETS ENUM ERROR: {e}"
        )

    # ============================================================
    # STEP 5
    # Not found
    # ============================================================

    print(
        f"GOOGLE SHEETS RESOLVE: "
        f"spreadsheet '{spreadsheet_name}' not found"
    )

    return None

async def _resolve_google_worksheet(user_id, mcp_url, spreadsheet_id, worksheet_name=None, tool_name="google_sheets_get_many_spreadsheet_rows_advanced"):

    manager = get_zapier_manager()

    worksheet_name = (worksheet_name or "").strip()

    print(
        "GOOGLE SHEETS WORKSHEET RESOLVE: "
        f"resolving worksheet='{worksheet_name}' "
        f"for spreadsheet_id='{spreadsheet_id}'"
    )

    # Continue to dynamic enum lookup below.

    try:

        enum_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="list_dynamic_enum_values",
            params={
                "tool_name": tool_name,
                "property_name": "worksheet",

                # IMPORTANT:
                # Dependency arguments must be passed inside tool_arguments
                "tool_arguments": {
                    "spreadsheet": spreadsheet_id
                },

                "search": ""
            }
        )

        print(
            "=== GOOGLE SHEETS WORKSHEET ENUM RESULT ==="
        )
        print(enum_result)
        print(
            "=== END GOOGLE SHEETS WORKSHEET ENUM RESULT ==="
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS WORKSHEET ENUM ERROR: "
            f"{e}"
        )

        return {
            "status": "ERROR",
            "worksheet": None,
            "message": "Unable to determine the worksheets.",
            "error": str(e)
        }

    # ============================================================
    # STEP 3
    # IMPORTANT: Check Zapier error BEFORE parsing values
    # ============================================================

    worksheet_enum_error = extract_zapier_error(
        enum_result
    )

    if worksheet_enum_error:

        print(
            "GOOGLE SHEETS WORKSHEET ENUM ERROR: "
            f"{worksheet_enum_error}"
        )

        return {
            "status": "ERROR",
            "worksheet": None,
            "spreadsheet_id": spreadsheet_id,
            "message": "Unable to determine the worksheets.",
            "error": worksheet_enum_error
        }

    # ============================================================
    # STEP 4
    # Parse dynamic enum
    # ============================================================

    data = enum_result

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:

                data = json.loads(text)

                break

            except Exception:

                continue

    if not isinstance(data, dict):

        return {
            "status": "ERROR",
            "worksheet": None,
            "spreadsheet_id": spreadsheet_id,
            "message": (
                "Invalid worksheet information "
                "was returned by Zapier."
            )
        }

    values = data.get("values")

    if not isinstance(values, list):

        return {
            "status": "ERROR",
            "worksheet": None,
            "spreadsheet_id": spreadsheet_id,
            "message": (
                "Zapier did not return a worksheet list."
            )
        }

    # ============================================================
    # STEP 5
    # Extract worksheet names
    # ============================================================

    worksheets = []

    for item in values:

        if not isinstance(item, dict):
            continue

        value = str(
            item.get("value") or ""
        ).strip()

        label = str(
            item.get("label") or value
        ).strip()

        if value:
            worksheets.append({
                "value": value,
                "label": label
            })

    print(
        "GOOGLE SHEETS WORKSHEETS FOUND: "
        f"{worksheets}"
    )

    # ============================================================
    # STEP 6
    # No worksheets
    # ============================================================

    if not worksheets:

        return {
            "status": "NOT_FOUND",
            "worksheet": None,
            "spreadsheet_id": spreadsheet_id,
            "message": (
                "No worksheets were found "
                "in the spreadsheet."
            )
        }

    # ============================================================
    # STEP 7
    # MATCH EXPLICITLY REQUESTED WORKSHEET
    # ============================================================

    if worksheet_name:

        normalized_requested = (
            worksheet_name
            .strip()
            .casefold()
        )

        matching_worksheets = []

        for item in worksheets:

            label = str(
                item.get("label") or ""
            ).strip()

            value = str(
                item.get("value") or ""
            ).strip()

            if (
                label.casefold()
                == normalized_requested
            ):

                matching_worksheets.append(item)

                continue

            if (
                value.casefold()
                == normalized_requested
            ):

                matching_worksheets.append(item)

        print(
            "GOOGLE SHEETS REQUESTED WORKSHEET MATCHES:",
            matching_worksheets
        )

        # --------------------------------------------------------
        # Exact worksheet found
        # --------------------------------------------------------

        if len(matching_worksheets) == 1:

            worksheet_value = (
                matching_worksheets[0]["value"]
            )

            worksheet_label = (
                matching_worksheets[0]["label"]
            )

            print(
                "GOOGLE SHEETS WORKSHEET RESOLVE: "
                f"requested='{worksheet_name}', "
                f"label='{worksheet_label}', "
                f"value='{worksheet_value}'"
            )

            return {
                "status": "FOUND",

                # Actual Zapier dynamic enum VALUE
                "worksheet": worksheet_value,

                # Human-readable worksheet name
                "worksheet_name": worksheet_label,

                "worksheets": worksheets
            }

        # --------------------------------------------------------
        # Worksheet was explicitly requested but not found
        # --------------------------------------------------------

        if not matching_worksheets:

            return {
                "status": "NOT_FOUND",
                "worksheet": None,
                "worksheet_name": worksheet_name,
                "worksheets": worksheets,
                "spreadsheet_id": spreadsheet_id,
                "message": (
                    f'Worksheet "{worksheet_name}" '
                    "could not be found."
                )
            }

        # --------------------------------------------------------
        # Ambiguous
        # --------------------------------------------------------

        return {
            "status": "MULTIPLE",
            "worksheet": None,
            "worksheets": matching_worksheets,
            "spreadsheet_id": spreadsheet_id,
            "message": (
                f'Multiple worksheets matched '
                f'"{worksheet_name}".'
            )
        }


    # ============================================================
    # STEP 8
    # NO WORKSHEET SUPPLIED
    # ============================================================

    if len(worksheets) == 1:

        worksheet_value = (
            worksheets[0]["value"]
        )

        worksheet_label = (
            worksheets[0]["label"]
        )

        print(
            "GOOGLE SHEETS WORKSHEET RESOLVE: "
            f"worksheet label='{worksheet_label}', "
            f"value='{worksheet_value}'"
        )

        return {
            "status": "FOUND",
            "worksheet": worksheet_value,
            "worksheet_name": worksheet_label,
            "worksheets": worksheets
        }


    # ============================================================
    # MULTIPLE WORKSHEETS AND NO WORKSHEET REQUESTED
    # ============================================================

    print(
        "GOOGLE SHEETS WORKSHEET RESOLVE: "
        f"multiple worksheets={worksheets}"
    )

    return {
        "status": "MULTIPLE",
        "worksheet": None,
        "worksheets": worksheets,
        "spreadsheet_id": spreadsheet_id,
        "message": (
            "Multiple worksheets were found. "
            "Please specify which worksheet to use."
        )
    }

def _parse_google_sheet_row_spec(rows_spec):
    """
    Convert:

        5
        1,3,5
        1-5
        1,3-5

    into a list of integer row numbers.
    """

    if rows_spec is None:
        return []

    text = str(
        rows_spec
    ).strip()

    if not text:
        return []

    result = set()

    for part in text.split(","):

        part = part.strip()

        if not part:
            continue

        # Range
        if "-" in part:

            pieces = part.split(
                "-",
                1
            )

            if len(pieces) != 2:
                raise ValueError(
                    f"Invalid row range '{part}'."
                )

            start = int(
                pieces[0].strip()
            )

            end = int(
                pieces[1].strip()
            )

            if start < 1 or end < 1:
                raise ValueError(
                    "Row numbers must be >= 1."
                )

            if end < start:
                raise ValueError(
                    f"Invalid row range '{part}'."
                )

            for row_number in range(
                start,
                end + 1
            ):

                result.add(
                    row_number
                )

        else:

            row_number = int(
                part
            )

            if row_number < 1:
                raise ValueError(
                    "Row numbers must be >= 1."
                )

            result.add(
                row_number
            )

    return sorted(
        result
    )

def extract_google_spreadsheet_id(result):
    """
    Extract Google Spreadsheet ID from a Zapier/MCP response.
    """

    if not result:
        return None

    # ============================================================
    # String
    # ============================================================

    if isinstance(result, str):

        try:

            data = json.loads(result)

            found = extract_google_spreadsheet_id(data)

            if found:
                return found

        except Exception:
            pass

        patterns = [
            r'"spreadsheetId"\s*:\s*"([^"]+)"',
            r'"spreadsheet_id"\s*:\s*"([^"]+)"',
            r'"file_id"\s*:\s*"([^"]+)"',
            r'"fileId"\s*:\s*"([^"]+)"',
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                result,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                if value and not value.startswith("lc_"):
                    return value

        return None

    # ============================================================
    # List
    # ============================================================

    if isinstance(result, list):

        for item in result:

            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if text:

                found = extract_google_spreadsheet_id(text)

                if found:
                    return found

            for key in ("spreadsheetId", "spreadsheet_id", "file_id", "fileId",):

                value = item.get(key)

                if (isinstance(value, str) and value.strip() and not value.startswith("lc_")):

                    return value.strip()

        return None

    # ============================================================
    # Dictionary
    # ============================================================

    if isinstance(result, dict):

        for key in ("spreadsheetId", "spreadsheet_id", "file_id", "fileId",):

            value = result.get(key)

            if (isinstance(value, str) and value.strip() and not value.startswith("lc_")):
                return value.strip()

        # Dynamic enum item:
        #
        # {
        #     "value": "1abc...",
        #     "label": "Sales Report"
        # }
        #

        value = result.get("value")

        if (isinstance(value, str) and value.strip() and not value.startswith("lc_")):

            return value.strip()

        # Search nested objects.
        for key, value in result.items():

            # Never interpret MCP's generic id as spreadsheet ID.
            if key == "id":
                continue

            found = extract_google_spreadsheet_id(value)

            if found:
                return found

    return None

def extract_google_spreadsheet_enum_value(result, spreadsheet_name=None):
    """
    Extract the spreadsheet ID from a Zapier
    dynamic-enum response.

    Example:

    {
        "values": [
            {
                "value": "1abc...",
                "label": "Sales Report"
            }
        ]
    }
    """

    if not result:
        return None

    data = result

    # ============================================================
    # MCP content block
    # ============================================================

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:

                data = json.loads(text)
                break

            except Exception:

                continue

    # ============================================================
    # Validate
    # ============================================================

    if not isinstance(data, dict):
        return None

    values = data.get("values")

    if not isinstance(values, list):
        return None

    # ============================================================
    # Exact spreadsheet name match
    # ============================================================

    if spreadsheet_name:

        wanted = (spreadsheet_name.strip().casefold())

        for item in values:

            if not isinstance(item, dict):
                continue

            label = str(item.get("label") or "").strip()

            value = item.get("value")

            if (label.casefold() == wanted and isinstance(value, str) and value.strip() and not value.startswith("lc_")):
                return value.strip()

    return None

def extract_google_sheet_rows(result):
    """
    Extract spreadsheet rows from a Zapier/MCP response.

    Returns a Python list containing the rows.
    """

    if not result:
        return []

    data = result

    # ============================================================
    # MCP content blocks
    # ============================================================

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                data = json.loads(text)
                break

            except Exception:
                continue

    # ============================================================
    # JSON object
    # ============================================================

    if isinstance(data, dict):

        # Common Zapier wrapper
        results = data.get("results")

        if isinstance(results, list):
            return results

        if isinstance(results, dict):

            for key in ("rows", "data", "values",):

                value = results.get(key)

                if isinstance(value, list):
                    return value

        # Direct response
        for key in ("rows", "data", "values",):

            value = data.get(key)

            if isinstance(value, list):
                return value

    # ============================================================
    # Direct list
    # ============================================================

    if isinstance(data, list):
        return data

    return []

def _google_sheet_values_equal(actual, expected) -> bool:
    """
    Compare Google Sheet values safely.

    Handles:
    - strings
    - integers
    - floats
    - numeric strings
    """

    if actual is None and expected is None:
        return True

    if actual is None or expected is None:
        return False

    # Try numeric comparison first.
    try:
        actual_number = float(str(actual).replace(",", "").strip())

        expected_number = float(str(expected).replace(",", "").strip())

        return actual_number == expected_number

    except (ValueError, TypeError):

        pass

    # Fall back to case-insensitive string comparison.
    return (str(actual).strip().casefold() == str(expected).strip().casefold())

def _evaluate_delete_condition(rows, condition):
    """
    Return spreadsheet row numbers matching the condition.

    condition:
    {
        "column": "Invoice no",
        "operator": "=",
        "value": "INV-1005"
    }
    """

    if not isinstance(condition, dict):
        return []

    column = str(
        condition.get("column") or ""
    ).strip()

    operator = str(
        condition.get("operator") or "="
    ).strip().lower()

    expected = condition.get("value")

    if not column:
        return []

    matched_rows = []

    for row in rows:

        if not isinstance(row, dict):
            continue

        row_number = row.get("row")

        if row_number is None:
            continue

        # --------------------------------------------------------
        # Find column value
        # --------------------------------------------------------

        actual = None

        if column in row:
            actual = row.get(column)

        else:

            # Case-insensitive column matching
            normalized_column = column.casefold()

            for key, value in row.items():

                if (
                    str(key).strip().casefold()
                    == normalized_column
                ):
                    actual = value
                    break

        if actual is None:
            continue

        actual_str = str(
            actual
        ).strip()

        expected_str = str(
            expected
        ).strip()

        # --------------------------------------------------------
        # Evaluate
        # --------------------------------------------------------

        matched = False

        if operator in ("=", "==", "eq"):

            matched = (
                actual_str.casefold()
                == expected_str.casefold()
            )

        elif operator in ("!=", "<>", "ne"):

            matched = (
                actual_str.casefold()
                != expected_str.casefold()
            )

        elif operator in (">", "gt"):

            try:
                matched = (
                    float(actual_str.replace(",", ""))
                    >
                    float(expected_str.replace(",", ""))
                )
            except (ValueError, TypeError):
                matched = actual_str > expected_str

        elif operator in (">=", "gte"):

            try:
                matched = (
                    float(actual_str.replace(",", ""))
                    >=
                    float(expected_str.replace(",", ""))
                )
            except (ValueError, TypeError):
                matched = actual_str >= expected_str

        elif operator in ("<", "lt"):

            try:
                matched = (
                    float(actual_str.replace(",", ""))
                    <
                    float(expected_str.replace(",", ""))
                )
            except (ValueError, TypeError):
                matched = actual_str < expected_str

        elif operator in ("<=", "lte"):

            try:
                matched = (
                    float(actual_str.replace(",", ""))
                    <=
                    float(expected_str.replace(",", ""))
                )
            except (ValueError, TypeError):
                matched = actual_str <= expected_str

        elif operator in ("contains", "includes"):

            matched = (
                expected_str.casefold()
                in
                actual_str.casefold()
            )

        elif operator in ("not_contains", "does_not_contain"):

            matched = (
                expected_str.casefold()
                not in
                actual_str.casefold()
            )

        if matched:

            matched_rows.append(
                int(row_number)
            )

    return sorted(
        set(matched_rows)
    )

async def _read_google_rows_for_condition(user_id, mcp_url, spreadsheet_id, worksheet):
    """
    Read Google Sheets rows once for condition evaluation.

    IMPORTANT:

    - Reads header row + data rows in ONE Zapier read call.
    - Does NOT call the high-level read_spreadsheet action.
    - Returns:
        {
            "status": "SUCCESS",
            "headers": {...},
            "rows": [...]
        }

    Example headers:

        {
            "date": "COL$A",
            "invoice no": "COL$B",
            "customer": "COL$C",
            "salesperson": "COL$D",
            ...
        }

    This allows conditions such as:

        {
            "column": "Client",
            "operator": "=",
            "value": "ABC Traders"
        }

    to correctly match a real sheet header such as:

        Customer
    """

    manager = get_zapier_manager()

    print(
        "GOOGLE SHEETS CONDITION READ:"
    )
    print(
        "  spreadsheet ID =",
        spreadsheet_id
    )
    print(
        "  worksheet      =",
        worksheet
    )

    try:

        read_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=(
                "google_sheets_get_many_spreadsheet_rows_advanced"
            ),
            params={
                "spreadsheet": spreadsheet_id,
                "worksheet": worksheet,

                # IMPORTANT:
                # Start at row 1 so we receive headers.
                "first_row": 1,

                "batch_size": 1500,

                "output_hint": (
                    "Return the complete worksheet data including "
                    "row number and every available column. "
                    "Include row 1 because it contains the column "
                    "headers. Do not omit any columns."
                )
            }
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS CONDITION READ EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "rows": [],
            "headers": {},
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS DELETE CONDITION READ RESULT ==="
    )
    print(read_result)
    print(
        "=== END GOOGLE SHEETS DELETE CONDITION READ RESULT ==="
    )

    # ============================================================
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        read_result
    )

    if error:

        print(
            "GOOGLE SHEETS CONDITION READ ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "rows": [],
            "headers": {},
            "error": error
        }

    # ============================================================
    # PARSE RESULT
    # ============================================================

    data = _parse_zapier_json_result(
        read_result
    )

    if not isinstance(data, dict):

        return {
            "status": "ERROR",
            "rows": [],
            "headers": {},
            "error": (
                "Invalid response returned by "
                "Google Sheets read operation."
            )
        }

    results = data.get(
        "results"
    )

    if not isinstance(
        results,
        list
    ):

        return {
            "status": "ERROR",
            "rows": [],
            "headers": {},
            "error": (
                "Google Sheets read operation did not "
                "return a row list."
            )
        }

    # ============================================================
    # STEP 1
    # NORMALIZE RAW RESULTS
    #
    # Zapier may return:
    #
    #   row
    #
    # OR:
    #
    #   row_number
    #
    # We support BOTH.
    # ============================================================

    normalized_rows = []

    for item in results:

        if not isinstance(
            item,
            dict
        ):
            continue

        row_number = (
            item.get("row")
            or item.get("row_number")
        )

        if row_number is None:

            # Some Zapier responses use "id".
            row_number = item.get(
                "id"
            )

        try:

            row_number = int(
                row_number
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        row_data = dict(
            item
        )

        row_data["row"] = row_number

        normalized_rows.append(
            row_data
        )

    print(
        "GOOGLE SHEETS CONDITION READ: "
        f"normalized {len(normalized_rows)} rows"
    )

    if not normalized_rows:

        return {
            "status": "SUCCESS",
            "headers": {},
            "rows": []
        }

    # ============================================================
    # STEP 2
    # FIND HEADER ROW
    #
    # Google Sheets header is expected to be row 1.
    # ============================================================

    header_row = None

    for row in normalized_rows:

        if row.get("row") == 1:

            header_row = row
            break

    # ============================================================
    # If Zapier did not return row 1, continue without
    # semantic header mapping.
    # ============================================================

    if not header_row:

        print(
            "GOOGLE SHEETS CONDITION READ: "
            "header row was not returned."
        )

        return {
            "status": "SUCCESS",
            "headers": {},
            "rows": [
                row
                for row in normalized_rows
                if row.get("row", 0) >= 2
            ]
        }

    # ============================================================
    # STEP 3
    # BUILD HEADER MAP
    #
    # Example:
    #
    # COL$A -> Date
    # COL$B -> Invoice No.
    # COL$C -> Customer
    #
    # Then:
    #
    # customer -> COL$C
    # invoice no -> COL$B
    # ============================================================

    headers = {}

    for key, value in header_row.items():

        if key in (
            "row",
            "row_number",
            "id"
        ):
            continue

        if value is None:
            continue

        header_text = str(
            value
        ).strip()

        if not header_text:
            continue

        normalized_header = (
            _normalize_google_sheet_column_name(
                header_text
            )
        )

        if not normalized_header:
            continue

        headers[
            normalized_header
        ] = key

    print(
        "GOOGLE SHEETS CONDITION HEADERS:",
        headers
    )

    # ============================================================
    # STEP 4
    # REMOVE HEADER ROW
    # ============================================================

    data_rows = []

    for row in normalized_rows:

        row_number = row.get(
            "row",
            0
        )

        if row_number <= 1:
            continue

        data_rows.append(
            row
        )

    print(
        "GOOGLE SHEETS CONDITION READ: "
        f"found {len(data_rows)} data rows"
    )

    return {
        "status": "SUCCESS",
        "headers": headers,
        "rows": data_rows
    }

def _parse_zapier_json_result(result):
    """
    Convert a Zapier MCP result into a Python dict/list.

    Handles:

        [
            {
                "type": "text",
                "text": "{...}"
            }
        ]

    and already-parsed dictionaries.
    """

    data = result

    if isinstance(
        data,
        list
    ):

        for block in data:

            if not isinstance(
                block,
                dict
            ):
                continue

            text = block.get(
                "text"
            )

            if not text:
                continue

            if isinstance(
                text,
                str
            ):

                try:

                    parsed = json.loads(
                        text
                    )

                    return parsed

                except (
                    json.JSONDecodeError,
                    TypeError
                ):

                    continue

    return data

def _parse_google_sheet_rows(rows):
    """
    Parse Google Sheets row specification.

    Supported:

        5
        "5"

        "2,5,7"

        "2-5"

        "1,3-5,8"

        [2, 5, 7]

        ["2", "5"]

    Returns:

        [2, 3, 4, 5, 8]
    """

    if rows is None:

        return []

    # ------------------------------------------------------------
    # Convert list/tuple/set into comma-separated specification
    # ------------------------------------------------------------

    if isinstance(
        rows,
        (list, tuple, set)
    ):

        parts = []

        for item in rows:

            parts.append(
                str(item)
            )

    else:

        parts = str(
            rows
        ).split(",")

    result = []

    for part in parts:

        part = str(
            part
        ).strip()

        if not part:
            continue

        # --------------------------------------------------------
        # Range
        # --------------------------------------------------------

        if "-" in part:

            range_parts = part.split(
                "-",
                1
            )

            if len(range_parts) != 2:

                raise ValueError(
                    f"Invalid row range '{part}'."
                )

            start_text = (
                range_parts[0].strip()
            )

            end_text = (
                range_parts[1].strip()
            )

            try:

                start = int(
                    start_text
                )

                end = int(
                    end_text
                )

            except ValueError:

                raise ValueError(
                    f"Invalid row range '{part}'."
                )

            if start <= 0 or end <= 0:

                raise ValueError(
                    "Row numbers must be greater than zero."
                )

            if start > end:

                raise ValueError(
                    f"Invalid row range '{part}': "
                    "start row is greater than end row."
                )

            result.extend(
                range(
                    start,
                    end + 1
                )
            )

            continue

        # --------------------------------------------------------
        # Single row
        # --------------------------------------------------------

        try:

            row_number = int(
                part
            )

        except ValueError:

            raise ValueError(
                f"Invalid row number '{part}'."
            )

        if row_number <= 0:

            raise ValueError(
                "Row numbers must be greater than zero."
            )

        result.append(
            row_number
        )

    return sorted(
        set(result)
    )

def _get_condition_column_value(row, requested_column, header_map=None):
    """
    Get a column value from a Google Sheets row.

    Supports:

        Customer
        Customer Name
        Client
        Invoice no
        Status

    and raw Zapier keys:

        COL$A
        COL$B
        COL$C
        ...

    `header_map` should map normalized human-readable headers
    to the corresponding raw Zapier column key.

    Example:

        {
            "date": "COL$A",
            "invoice no": "COL$B",
            "customer": "COL$C",
            "salesperson": "COL$D"
        }
    """

    if not isinstance(row, dict):
        return None

    requested = str(
        requested_column or ""
    ).strip()

    if not requested:
        return None

    # ============================================================
    # 1. EXACT RAW KEY
    # ============================================================

    if requested in row:
        return row.get(requested)

    # ============================================================
    # 2. CASE-INSENSITIVE RAW KEY
    # ============================================================

    requested_lower = requested.casefold()

    for key, value in row.items():

        if (
            str(key).strip().casefold()
            == requested_lower
        ):
            return value

    # ============================================================
    # 3. NORMALIZED HEADER LOOKUP
    # ============================================================

    requested_normalized = (
        _normalize_google_sheet_column_name(
            requested
        )
    )

    if header_map:

        # Exact normalized header
        raw_key = header_map.get(
            requested_normalized
        )

        if raw_key in row:
            return row.get(raw_key)

    # ============================================================
    # 4. COMMON SEMANTIC ALIASES
    # ============================================================

    aliases = {
        "customer": [
            "customer",
            "customer name",
            "client",
            "client name",
            "customer_name",
            "client_name"
        ],

        "customer name": [
            "customer",
            "customer name",
            "client",
            "client name",
            "customer_name",
            "client_name"
        ],

        "client": [
            "client",
            "client name",
            "customer",
            "customer name",
            "client_name",
            "customer_name"
        ],

        "client name": [
            "client",
            "client name",
            "customer",
            "customer name",
            "client_name",
            "customer_name"
        ],

        "invoice": [
            "invoice",
            "invoice no",
            "invoice number",
            "invoice_no",
            "invoice_number"
        ],

        "invoice no": [
            "invoice",
            "invoice no",
            "invoice number",
            "invoice_no",
            "invoice_number"
        ],

        "invoice number": [
            "invoice",
            "invoice no",
            "invoice number",
            "invoice_no",
            "invoice_number"
        ]
    }

    requested_aliases = aliases.get(
        requested_normalized,
        []
    )

    # ============================================================
    # 5. TRY ALIASES AGAINST HEADER MAP
    # ============================================================

    if header_map:

        for alias in requested_aliases:

            alias_normalized = (
                _normalize_google_sheet_column_name(
                    alias
                )
            )

            raw_key = header_map.get(
                alias_normalized
            )

            if raw_key in row:
                return row.get(raw_key)

    # ============================================================
    # 6. FALLBACK: NORMALIZED RAW KEYS
    # ============================================================

    for key, value in row.items():

        key_normalized = (
            _normalize_google_sheet_column_name(
                key
            )
        )

        if (
            key_normalized
            == requested_normalized
        ):
            return value

    return None

def _compress_google_sheet_rows(rows):
    """
    Convert row numbers into a compact Zapier specification.

    Example:

        [1, 3, 4, 5, 8]

    becomes:

        "1,3-5,8"
    """

    if not rows:

        return ""

    numbers = sorted(
        set(
            int(row)
            for row in rows
        )
    )

    ranges = []

    start = numbers[0]
    previous = numbers[0]

    for number in numbers[1:]:

        if number == previous + 1:

            previous = number
            continue

        if start == previous:

            ranges.append(
                str(start)
            )

        else:

            ranges.append(
                f"{start}-{previous}"
            )

        start = number
        previous = number

    # ------------------------------------------------------------
    # Final range
    # ------------------------------------------------------------

    if start == previous:

        ranges.append(
            str(start)
        )

    else:

        ranges.append(
            f"{start}-{previous}"
        )

    return ",".join(
        ranges
    )


    """
    Get a column value from a Google Sheets row.

    Supports human-readable names such as:

        Invoice no
        Status
        Salary

    and raw keys such as:

        COL_A
        COL_B
        COL_K

    Also handles common aliases such as:

        invoice
        invoice no
        invoice number
    """

    if not isinstance(
        row,
        dict
    ):

        return None

    requested = str(
        requested_column or ""
    ).strip()

    if not requested:

        return None

    # ============================================================
    # EXACT MATCH
    # ============================================================

    if requested in row:

        return row.get(
            requested
        )

    # ============================================================
    # CASE-INSENSITIVE MATCH
    # ============================================================

    requested_lower = requested.casefold()

    for key, value in row.items():

        if str(
            key
        ).strip().casefold() == requested_lower:

            return value

    # ============================================================
    # NORMALIZED MATCH
    # ============================================================

    requested_normalized = (
        _normalize_google_sheet_column_name(
            requested
        )
    )

    for key, value in row.items():

        key_normalized = (
            _normalize_google_sheet_column_name(
                key
            )
        )

        if (
            key_normalized
            == requested_normalized
        ):

            return value

    # ============================================================
    # COMMON COLUMN ALIASES
    # ============================================================

    aliases = {
        "invoice": [
            "invoice",
            "invoice no",
            "invoice number",
            "invoice_no",
            "invoice_number"
        ],

        "invoice no": [
            "invoice",
            "invoice no",
            "invoice number",
            "invoice_no",
            "invoice_number"
        ],

        "invoice number": [
            "invoice",
            "invoice no",
            "invoice number",
            "invoice_no",
            "invoice_number"
        ]
    }

    requested_aliases = aliases.get(
        requested_normalized,
        []
    )

    for alias in requested_aliases:

        alias_normalized = (
            _normalize_google_sheet_column_name(
                alias
            )
        )

        for key, value in row.items():

            if (
                _normalize_google_sheet_column_name(
                    key
                )
                == alias_normalized
            ):

                return value

    # ============================================================
    # RETURN NONE
    # ============================================================

    return None

def _normalize_google_sheet_column_name(value):
    """
    Normalize a Google Sheets column name for comparison.
    """

    return (
        str(value or "")
        .strip()
        .casefold()
        .replace("_", "")
        .replace("-", "")
        .replace(" ", "")
    )

def _evaluate_google_sheet_condition(actual_value, operator, expected_value):
    """
    Evaluate one Google Sheets condition.

    Supported operators:

        =
        ==
        !=
        <>
        >
        >=
        <
        <=
        contains
        not_contains
        starts_with
        ends_with
    """

    operator = str(
        operator or "="
    ).strip().casefold()

    # ============================================================
    # NORMALIZE STRING VALUES
    # ============================================================

    actual_text = str(
        actual_value
        if actual_value is not None
        else ""
    ).strip()

    expected_text = str(
        expected_value
        if expected_value is not None
        else ""
    ).strip()

    # ============================================================
    # EQUALITY
    # ============================================================

    if operator in (
        "=",
        "==",
        "equals",
        "equal"
    ):

        return (
            actual_text.casefold()
            == expected_text.casefold()
        )

    # ============================================================
    # NOT EQUAL
    # ============================================================

    if operator in (
        "!=",
        "<>",
        "not_equals",
        "not equal"
    ):

        return (
            actual_text.casefold()
            != expected_text.casefold()
        )

    # ============================================================
    # CONTAINS
    # ============================================================

    if operator in (
        "contains",
        "contain"
    ):

        return (
            expected_text.casefold()
            in actual_text.casefold()
        )

    # ============================================================
    # NOT CONTAINS
    # ============================================================

    if operator in (
        "not_contains",
        "does_not_contain",
        "not contains"
    ):

        return (
            expected_text.casefold()
            not in actual_text.casefold()
        )

    # ============================================================
    # STARTS WITH
    # ============================================================

    if operator in (
        "starts_with",
        "starts with"
    ):

        return actual_text.casefold().startswith(
            expected_text.casefold()
        )

    # ============================================================
    # ENDS WITH
    # ============================================================

    if operator in (
        "ends_with",
        "ends with"
    ):

        return actual_text.casefold().endswith(
            expected_text.casefold()
        )

    # ============================================================
    # NUMERIC COMPARISON
    # ============================================================

    actual_number = (
        _google_sheet_to_number(
            actual_value
        )
    )

    expected_number = (
        _google_sheet_to_number(
            expected_value
        )
    )

    if (
        actual_number is None
        or expected_number is None
    ):

        return False

    if operator == ">":

        return actual_number > expected_number

    if operator == ">=":

        return actual_number >= expected_number

    if operator == "<":

        return actual_number < expected_number

    if operator == "<=":

        return actual_number <= expected_number

    # ============================================================
    # UNKNOWN OPERATOR
    # ============================================================

    return False

def _google_sheet_to_number(value):
    """
    Convert Google Sheets numeric-looking values into float.

    Handles examples such as:

        50000
        "50000"
        "50,000"
        "₹70,000"
        "$70,000"
        "₹1,27,440"
        " 50000 "
    """

    if value is None:

        return None

    if isinstance(
        value,
        bool
    ):

        return None

    if isinstance(
        value,
        (int, float)
    ):

        return float(
            value
        )

    text = str(
        value
    ).strip()

    if not text:

        return None

    # ------------------------------------------------------------
    # Remove currency symbols and separators.
    # ------------------------------------------------------------

    cleaned = (
        text
        .replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("%", "")
        .strip()
    )

    # ------------------------------------------------------------
    # Parentheses mean negative number.
    #
    # Example:
    #     (5000)
    # ------------------------------------------------------------

    negative = False

    if (
        cleaned.startswith("(")
        and cleaned.endswith(")")
    ):

        negative = True

        cleaned = cleaned[1:-1].strip()

    try:

        number = float(
            cleaned
        )

    except (
        ValueError,
        TypeError
    ):

        return None

    if negative:

        number = -number

    return number

async def _find_google_spreadsheet(user_id, mcp_url, params):

    manager = get_zapier_manager()

    spreadsheet_name = (params.get("spreadsheet_name") or params.get("title") or "").strip()

    search_type = (params.get("search_type") or "exact").strip().lower()

    print("=" * 60)
    print("GOOGLE SHEETS FIND SPREADSHEET")
    print(f"SPREADSHEET NAME : {spreadsheet_name}")
    print(f"SEARCH TYPE      : {search_type}")
    print("=" * 60)

    # ------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------

    if not spreadsheet_name:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "find_spreadsheet",
            "message": (
                "Please provide a spreadsheet name."
            )
        }

    # ------------------------------------------------------------
    # Validate search type
    # ------------------------------------------------------------

    if search_type not in ("exact", "contains"):

        search_type = "exact"

    # ------------------------------------------------------------
    # Find spreadsheet
    # ------------------------------------------------------------

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,

            tool_name="google_sheets_find_spreadsheet",

            params={
                "title": spreadsheet_name,
                "search_type": search_type,

                "output_hint": (
                    "Return matching spreadsheets with "
                    "spreadsheet name, spreadsheet ID, "
                    "and spreadsheet URL."
                )
            }
        )

        print("")
        print("=== GOOGLE SHEETS FIND RAW RESULT ===")
        print(result)
        print("=== END GOOGLE SHEETS FIND RESULT ===")
        print("")

        # --------------------------------------------------------
        # Check Zapier/MCP error
        # --------------------------------------------------------

        error = extract_zapier_error(result)

        if error:

            print(
                f"=== GOOGLE SHEETS FIND ERROR === "
                f"{error}"
            )

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "find_spreadsheet",
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    "Unable to search for the "
                    "Google Spreadsheet."
                ),
                "error": error
            }

        # --------------------------------------------------------
        # Return normalized result
        # --------------------------------------------------------

        return {
            "status": "SUCCESS",
            "app": "google_sheets",
            "action": "find_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "search_type": search_type,
            "data": result
        }

    except Exception as e:

        print(
            f"GOOGLE SHEETS FIND EXCEPTION: {e}"
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "find_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "Unable to find the Google Spreadsheet."
            ),
            "error": str(e)
        }

async def _delete_google_spreadsheet(user_id, mcp_url, params):
    """
    Permanently delete a Google Spreadsheet.

    Expected input:

        {
            "spreadsheet_name": "Employee"
        }

    OR:

        {
            "spreadsheet_id": "1abc..."
        }

    IMPORTANT:
    - This permanently deletes the Google Sheets file.
    - The spreadsheet must first be resolved to its file ID.
    - Do not delete by spreadsheet name directly.
    - Only return SUCCESS when the MCP delete operation explicitly
      reports success.
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_id = (
        params.get("spreadsheet_id") or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name") or ""
    ).strip()

    print("=" * 70)
    print("GOOGLE SHEETS DELETE SPREADSHEET")
    print("SPREADSHEET NAME :", spreadsheet_name)
    print("SPREADSHEET ID   :", spreadsheet_id)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not spreadsheet_id and not spreadsheet_name:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    # ============================================================
    # STEP 1
    # RESOLVE SPREADSHEET ID
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS DELETE SPREADSHEET: "
            f"resolving spreadsheet '{spreadsheet_name}'"
        )

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name="google_drive_delete_file",
                enum_property_name="fileId"
            )
        )

        print(
            "GOOGLE SHEETS DELETE SPREADSHEET: "
            f"resolved spreadsheet ID={spreadsheet_id}"
        )

    # ============================================================
    # NOT FOUND
    # ============================================================

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "delete_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f"Google Spreadsheet "
                f"'{spreadsheet_name}' could not be found."
            )
        }

    # ============================================================
    # STEP 2
    # DELETE FILE
    # ============================================================

    print(
        "GOOGLE SHEETS DELETE SPREADSHEET:"
    )

    print(
        "  spreadsheet ID =",
        spreadsheet_id
    )

    print(
        "  tool           =",
        "google_drive_delete_file"
    )

    try:

        delete_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_drive_delete_file",
            params={
                "fileId": spreadsheet_id,
                "output_hint": (
                    "Confirm whether the specified Google "
                    "Spreadsheet file was permanently deleted. "
                    "Return the deletion result and file ID."
                )
            }
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS DELETE SPREADSHEET EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "Unable to delete the Google Spreadsheet."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS DELETE SPREADSHEET RAW RESULT ==="
    )

    print(delete_result)

    print(
        "=== END GOOGLE SHEETS DELETE SPREADSHEET RAW RESULT ==="
    )

    # ============================================================
    # STEP 3
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        delete_result
    )

    if error:

        print(
            "GOOGLE SHEETS DELETE SPREADSHEET ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f'The Google Spreadsheet '
                f'"{spreadsheet_name or spreadsheet_id}" '
                "could not be deleted."
            ),
            "error": error
        }

    # ============================================================
    # STEP 4
    # PARSE RAW RESULT
    # ============================================================

    result_data = delete_result

    if isinstance(result_data, list):

        for block in result_data:

            if not isinstance(
                block,
                dict
            ):
                continue

            text = block.get(
                "text"
            )

            if not text:
                continue

            try:

                parsed = json.loads(
                    text
                )

                if isinstance(
                    parsed,
                    dict
                ):

                    result_data = parsed

                    break

            except Exception:

                continue

    # ============================================================
    # STEP 5
    # EXPLICIT MCP ERROR
    # ============================================================

    if isinstance(result_data, dict):

        if result_data.get("isError"):

            error_message = (
                result_data.get(
                    "error"
                )
                or
                "Google Drive delete operation failed."
            )

            print(
                "GOOGLE SHEETS DELETE SPREADSHEET MCP ERROR:",
                error_message
            )

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    f'The Google Spreadsheet '
                    f'"{spreadsheet_name or spreadsheet_id}" '
                    "could not be deleted."
                ),
                "error": error_message
            }

        # ========================================================
        # GOOGLE DRIVE DELETE RESPONSE
        #
        # Actual MCP response:
        #
        # {
        #     "results": {
        #         "deletion_result":
        #             "File successfully deleted",
        #         "file_id": null
        #     }
        # }
        # ========================================================

        results = result_data.get(
            "results"
        )

        if isinstance(results, dict):

            deletion_result = str(
                results.get(
                    "deletion_result"
                ) or ""
            ).strip()

            print(
                "GOOGLE SHEETS DELETE SPREADSHEET "
                "DELETION RESULT:",
                deletion_result
            )

            # ====================================================
            # EXPLICIT SUCCESS
            # ====================================================

            if (
                "successfully deleted"
                in deletion_result.casefold()
            ):

                print(
                    "GOOGLE SHEETS DELETE SPREADSHEET: "
                    "DELETE OPERATION SUCCESSFUL"
                )

                return {
                    "status": "SUCCESS",
                    "app": "google_sheets",
                    "action": "delete_spreadsheet",
                    "spreadsheet_id": spreadsheet_id,
                    "spreadsheet_name": spreadsheet_name,
                    "message": (
                        f'Google Spreadsheet '
                        f'"{spreadsheet_name or spreadsheet_id}" '
                        "was successfully deleted."
                    ),
                    "deletion_result": deletion_result
                }

    # ============================================================
    # ALSO SUPPORT GENERIC RESULT="success"
    #
    # Keep this in case another version of the MCP tool returns
    # the simpler success format.
    # ============================================================

    if isinstance(result_data, dict):

        result_value = str(
            result_data.get(
                "result"
            ) or ""
        ).strip().casefold()

        if result_value == "success":

            print(
                "GOOGLE SHEETS DELETE SPREADSHEET: "
                "DELETE OPERATION SUCCESSFUL"
            )

            return {
                "status": "SUCCESS",
                "app": "google_sheets",
                "action": "delete_spreadsheet",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    f'Google Spreadsheet '
                    f'"{spreadsheet_name or spreadsheet_id}" '
                    "was successfully deleted."
                )
            }

    # ============================================================
    # FALLBACK
    #
    # Do NOT claim success when MCP did not explicitly report it.
    # ============================================================

    return {
        "status": "ERROR",
        "app": "google_sheets",
        "action": "delete_spreadsheet",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_name": spreadsheet_name,
        "message": (
            f'The Google Spreadsheet '
            f'"{spreadsheet_name or spreadsheet_id}" '
            "could not be confirmed as deleted."
        ),
        "raw_result": result_data
    }

async def _delete_google_worksheet(user_id, mcp_url, params):
    """
    Permanently delete a worksheet/tab from a Google Spreadsheet.

    Expected input:

        {
            "spreadsheet_name": "Customer",
            "worksheet": "Sheet2"
        }

    OR:

        {
            "spreadsheet_id": "1abc...",
            "worksheet": "Sheet2"
        }

    IMPORTANT:

    - Deletes ONLY the worksheet/tab.
    - Does NOT delete the parent spreadsheet.
    - The Zapier delete tool requires:
          confirmation = "DELETE"
    - The worksheet is resolved through Zapier's dynamic enum.
    - The human worksheet name is matched against the enum label.
    - The actual enum value is passed to the delete tool.
    - Exactly ONE delete operation is executed.
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_id = (
        params.get("spreadsheet_id") or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name") or ""
    ).strip()

    requested_worksheet = (
        params.get("worksheet") or ""
    ).strip()

    print("=" * 70)
    print("GOOGLE SHEETS DELETE WORKSHEET")
    print("SPREADSHEET NAME :", spreadsheet_name)
    print("SPREADSHEET ID   :", spreadsheet_id)
    print("REQUESTED SHEET  :", requested_worksheet)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not spreadsheet_id and not spreadsheet_name:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    if not requested_worksheet:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "message": (
                "Please provide the worksheet name "
                "to delete."
            )
        }

    # ============================================================
    # STEP 1
    # RESOLVE SPREADSHEET
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS DELETE WORKSHEET: "
            f"resolving spreadsheet '{spreadsheet_name}'"
        )

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name="google_sheets_delete_sheet",
                enum_property_name="spreadsheet"
            )
        )

        print(
            "GOOGLE SHEETS DELETE WORKSHEET: "
            f"resolved spreadsheet ID={spreadsheet_id}"
        )

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "message": (
                f'Google Spreadsheet "{spreadsheet_name}" '
                "could not be found."
            )
        }

    # ============================================================
    # STEP 2
    # RESOLVE WORKSHEET DYNAMIC ENUM
    #
    # IMPORTANT:
    #
    # Do NOT pass "Sheet2" directly.
    #
    # We need the Zapier dynamic enum value corresponding
    # to the human worksheet name.
    # ============================================================

    worksheet_result = await _resolve_google_worksheet(
        user_id=user_id,
        mcp_url=mcp_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=requested_worksheet,
        tool_name="google_sheets_delete_sheet"
    )

    print(
        "GOOGLE SHEETS DELETE WORKSHEET RESOLVE:",
        worksheet_result
    )

    # ============================================================
    # STEP 3
    # HANDLE RESOLUTION RESULT
    # ============================================================

    if not isinstance(
        worksheet_result,
        dict
    ):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "message": (
                "Invalid worksheet resolution result."
            )
        }

    # ------------------------------------------------------------
    # NOT FOUND
    # ------------------------------------------------------------

    if worksheet_result.get(
        "status"
    ) == "NOT_FOUND":

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "message": (
                f'The worksheet "{requested_worksheet}" '
                f'could not be found in the '
                f'"{spreadsheet_name}" spreadsheet.'
            )
        }

    # ------------------------------------------------------------
    # MULTIPLE
    #
    # For an explicit worksheet name, our resolver should
    # normally return FOUND after matching the requested label.
    # But don't guess if it returns MULTIPLE.
    # ------------------------------------------------------------

    if worksheet_result.get(
        "status"
    ) == "MULTIPLE":

        worksheets = (
            worksheet_result.get(
                "worksheets"
            )
            or []
        )

        return {
            "status": "MULTIPLE_WORKSHEETS",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "worksheets": worksheets,
            "message": (
                f'Multiple worksheets could not be '
                f'resolved for "{requested_worksheet}" '
                f'in the "{spreadsheet_name}" spreadsheet.'
            )
        }

    # ------------------------------------------------------------
    # ERROR
    # ------------------------------------------------------------

    if worksheet_result.get(
        "status"
    ) == "ERROR":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "message": worksheet_result.get(
                "message",
                "Unable to determine worksheet."
            ),
            "error": worksheet_result.get(
                "error"
            )
        }

    # ============================================================
    # STEP 4
    # GET ACTUAL ZAPIER ENUM VALUE
    # ============================================================

    worksheet_value = str(
        worksheet_result.get(
            "worksheet"
        ) or ""
    ).strip()

    worksheet_label = str(
        worksheet_result.get(
            "worksheet_name"
        )
        or requested_worksheet
    ).strip()

    if not worksheet_value:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "message": (
                "Unable to determine the actual "
                "Zapier worksheet value."
            )
        }

    print("=" * 70)
    print("GOOGLE SHEETS DELETE WORKSHEET RESOLVED")
    print("SPREADSHEET ID :", spreadsheet_id)
    print("REQUESTED       :", requested_worksheet)
    print("WORKSHEET LABEL :", worksheet_label)
    print("WORKSHEET VALUE :", worksheet_value)
    print("CONFIRMATION    : DELETE")
    print("=" * 70)

    # ============================================================
    # STEP 5
    # EXECUTE EXACTLY ONE DELETE
    # ============================================================

    try:

        delete_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_sheets_delete_sheet",
            params={
                "spreadsheet": spreadsheet_id,

                # IMPORTANT:
                # Pass the dynamic enum VALUE, not the label.
                "worksheet": worksheet_value,

                "confirmation": "DELETE",

                "output_hint": (
                    "Return only the result of the "
                    "worksheet deletion operation."
                )
            }
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS DELETE WORKSHEET EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet_label,
            "message": (
                "Unable to delete the Google "
                "Sheets worksheet."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS DELETE WORKSHEET RAW RESULT ==="
    )
    print(delete_result)
    print(
        "=== END GOOGLE SHEETS DELETE WORKSHEET RAW RESULT ==="
    )

    # ============================================================
    # STEP 6
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        delete_result
    )

    if error:

        print(
            "GOOGLE SHEETS DELETE WORKSHEET ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_worksheet",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet_label,
            "message": (
                f'The worksheet "{worksheet_label}" '
                f'could not be deleted from the '
                f'"{spreadsheet_name}" spreadsheet.'
            ),
            "error": error
        }

    # ============================================================
    # STEP 7
    # PARSE RESULT
    # ============================================================

    result_data = delete_result

    if isinstance(
        result_data,
        list
    ):

        for block in result_data:

            if not isinstance(
                block,
                dict
            ):
                continue

            text = block.get(
                "text"
            )

            if not text:
                continue

            try:

                parsed = json.loads(
                    text
                )

                if isinstance(
                    parsed,
                    dict
                ):

                    result_data = parsed
                    break

            except Exception:

                continue

    # ============================================================
    # STEP 8
    # EXPLICIT MCP ERROR
    # ============================================================

    if isinstance(
        result_data,
        dict
    ):

        if result_data.get(
            "isError"
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_worksheet",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_label,
                "message": (
                    f'The worksheet "{worksheet_label}" '
                    f'could not be deleted from the '
                    f'"{spreadsheet_name}" spreadsheet.'
                ),
                "error": (
                    result_data.get(
                        "error"
                    )
                    or
                    "Google Sheets delete operation failed."
                )
            }

        # --------------------------------------------------------
        # Explicit success returned by Zapier
        # --------------------------------------------------------

        result_value = str(
            result_data.get(
                "result"
            ) or ""
        ).strip().casefold()

        if result_value == "success":

            print(
                "GOOGLE SHEETS DELETE WORKSHEET: "
                "DELETE OPERATION SUCCESSFUL"
            )

            return {
                "status": "SUCCESS",
                "app": "google_sheets",
                "action": "delete_worksheet",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_label,
                "message": (
                    f'Worksheet "{worksheet_label}" '
                    f'was successfully deleted from '
                    f'the "{spreadsheet_name}" spreadsheet.'
                )
            }

    # ============================================================
    # STEP 9
    # UNKNOWN RESULT
    # ============================================================

    return {
        "status": "ERROR",
        "app": "google_sheets",
        "action": "delete_worksheet",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_name": spreadsheet_name,
        "worksheet": worksheet_label,
        "message": (
            f'The worksheet "{worksheet_label}" '
            f'could not be confirmed as deleted '
            f'from the "{spreadsheet_name}" spreadsheet.'
        ),
        "raw_result": result_data
    }    


    """
    Delete one or more rows from a Google Spreadsheet worksheet.

    Expected input:

        {
            "spreadsheet_name": "Employee",
            "worksheet": "Sheet1",
            "rows": "5"
        }

    OR:

        {
            "spreadsheet_id": "1abc...",
            "worksheet": "Sheet1",
            "rows": "5,8,10"
        }

    Supported row formats:

        "5"
        "1,3,5"
        "1-5"
        "1,3-5"

    IMPORTANT:

    - Deletes spreadsheet rows only.
    - Does NOT delete the worksheet.
    - Does NOT delete the spreadsheet.
    - The MCP tool accepts row numbers/ranges through `rows`.
    - The MCP tool does NOT have a confirmation parameter.
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_id = (
        params.get("spreadsheet_id") or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name") or ""
    ).strip()

    requested_worksheet = (
        params.get("worksheet") or ""
    ).strip()

    rows = (
        params.get("rows") or ""
    ).strip()

    print("=" * 70)
    print("GOOGLE SHEETS DELETE ROWS")
    print("SPREADSHEET NAME :", spreadsheet_name)
    print("SPREADSHEET ID   :", spreadsheet_id)
    print("WORKSHEET        :", requested_worksheet)
    print("ROWS             :", rows)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not spreadsheet_id and not spreadsheet_name:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    if not requested_worksheet:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "message": (
                "Please provide the worksheet name "
                "from which rows should be deleted."
            )
        }

    if not rows:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": requested_worksheet,
            "message": (
                "Please provide the row number or row range "
                "to delete."
            )
        }

    # ============================================================
    # STEP 1
    # VALIDATE ROW SPECIFICATION
    # ============================================================
    #
    # Supported:
    #
    #   5
    #   1,3,5
    #   1-5
    #   1,3-5
    #
    # We validate the syntax before sending it to Zapier.
    #
    # ============================================================

    row_specification = rows.replace(" ", "")

    row_parts = row_specification.split(",")

    invalid_parts = []

    normalized_parts = []

    for part in row_parts:

        if not part:
            invalid_parts.append(part)
            continue

        # Single row
        if re.fullmatch(r"\d+", part):

            row_number = int(part)

            if row_number < 1:
                invalid_parts.append(part)
                continue

            normalized_parts.append(
                str(row_number)
            )

            continue

        # Row range
        if re.fullmatch( r"\d+-\d+", part):

            start_str, end_str = part.split("-", 1)

            start_row = int(start_str)
            end_row = int(end_str)

            if (start_row < 1 or end_row < 1 or start_row > end_row):

                invalid_parts.append(part)
                continue

            normalized_parts.append(
                f"{start_row}-{end_row}"
            )

            continue

        invalid_parts.append(part)

    if invalid_parts:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": requested_worksheet,
            "rows": rows,
            "message": (
                f"Invalid row specification '{rows}'. "
                "Use formats such as '5', '1,3,5', "
                "'1-5', or '1,3-5'."
            ),
            "invalid_parts": invalid_parts
        }

    rows = ",".join(
        normalized_parts
    )

    print(
        "GOOGLE SHEETS DELETE ROWS: "
        f"validated rows='{rows}'"
    )

    # ============================================================
    # STEP 2
    # RESOLVE SPREADSHEET
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            f"resolving spreadsheet '{spreadsheet_name}'"
        )

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name=(
                    "google_sheets_delete_spreadsheet_row_s"
                ),
                enum_property_name="spreadsheet"
            )
        )

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            f"resolved spreadsheet ID={spreadsheet_id}"
        )

    # ============================================================
    # SPREADSHEET NOT FOUND
    # ============================================================

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_name": spreadsheet_name,
            "worksheet": requested_worksheet,
            "rows": rows,
            "message": (
                f"Google Spreadsheet "
                f"'{spreadsheet_name}' could not be found."
            )
        }

    # ============================================================
    # IMPORTANT
    #
    # Do NOT call _resolve_google_worksheet() here.
    #
    # The delete_worksheet operation taught us that passing the
    # user-supplied worksheet directly is the reliable approach
    # for the actual delete tool.
    #
    # The MCP schema accepts:
    #
    #     worksheet: string
    #
    # Therefore:
    #
    #     "Sheet1"
    #
    # is passed directly.
    # ============================================================

    worksheet = requested_worksheet

    print(
        "GOOGLE SHEETS DELETE ROWS:"
    )
    print(
        "  spreadsheet ID =",
        spreadsheet_id
    )
    print(
        "  worksheet      =",
        worksheet
    )
    print(
        "  rows           =",
        rows
    )

    # ============================================================
    # STEP 3
    # EXECUTE ZAPIER DELETE ROWS TOOL
    # ============================================================

    try:

        delete_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=(
                "google_sheets_delete_spreadsheet_row_s"
            ),
            params={
                "spreadsheet": spreadsheet_id,
                "worksheet": worksheet,
                "rows": rows,
                "output_hint": (
                    "Confirm that the specified row or rows "
                    "were successfully deleted from the "
                    "specified worksheet in the Google "
                    "Spreadsheet."
                )
            }
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS DELETE ROWS EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet,
            "rows": rows,
            "message": (
                "Unable to delete the specified "
                "Google Sheets rows."
            ),
            "error": str(e)
        }

    # ============================================================
    # RAW RESULT
    # ============================================================

    print(
        "=== GOOGLE SHEETS DELETE ROWS RAW RESULT ==="
    )
    print(delete_result)
    print(
        "=== END GOOGLE SHEETS DELETE ROWS RAW RESULT ==="
    )

    # ============================================================
    # STEP 4
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        delete_result
    )

    if error:

        print(
            "GOOGLE SHEETS DELETE ROWS ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet,
            "rows": rows,
            "message": (
                f"The rows '{rows}' could not be "
                f"deleted from worksheet "
                f"'{worksheet}'."
            ),
            "error": error
        }

    # ============================================================
    # STEP 5
    # PARSE RAW RESULT
    # ============================================================

    result_data = delete_result

    if isinstance(result_data, list):

        for block in result_data:

            if not isinstance(
                block,
                dict
            ):
                continue

            text = block.get(
                "text"
            )

            if not text:
                continue

            try:

                parsed = json.loads(
                    text
                )

                if isinstance(
                    parsed,
                    dict
                ):

                    result_data = parsed
                    break

            except Exception:

                continue

    # ============================================================
    # STEP 6
    # EXPLICIT MCP ERROR
    # ============================================================

    if isinstance(result_data, dict):

        if result_data.get(
            "isError"
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "rows": rows,
                "message": (
                    f"The rows '{rows}' could not be "
                    f"deleted from worksheet "
                    f"'{worksheet}'."
                ),
                "error": (
                    result_data.get(
                        "error"
                    )
                    or
                    "Google Sheets row deletion failed."
                )
            }

    # ============================================================
    # STEP 7
    # CHECK EXPLICIT SUCCESS
    # ============================================================

    if isinstance(result_data, dict):

        result_value = str(
            result_data.get(
                "result"
            ) or ""
        ).strip().casefold()

        if result_value == "success":

            print(
                "GOOGLE SHEETS DELETE ROWS: "
                "DELETE OPERATION SUCCESSFUL"
            )

            return {
                "status": "SUCCESS",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "rows": rows,
                "message": (
                    f"Rows '{rows}' were successfully "
                    f"deleted from worksheet "
                    f"'{worksheet}' in the "
                    f"'{spreadsheet_name}' spreadsheet."
                )
            }

    # ============================================================
    # STEP 8
    # SOME ZAPIER ACTIONS RETURN RESULTS WITHOUT
    # A TOP-LEVEL "result": "success".
    #
    # If there is no explicit error and Zapier returned a
    # meaningful result, inspect common success indicators.
    # ============================================================

    if isinstance(result_data, dict):

        results = result_data.get(
            "results"
        )

        if results is not None:

            print(
                "GOOGLE SHEETS DELETE ROWS: "
                "Zapier returned results without an "
                "explicit error."
            )

            return {
                "status": "SUCCESS",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "rows": rows,
                "message": (
                    f"Rows '{rows}' were successfully "
                    f"deleted from worksheet "
                    f"'{worksheet}' in the "
                    f"'{spreadsheet_name}' spreadsheet."
                )
            }

    # ============================================================
    # STEP 9
    # FALLBACK
    #
    # Never claim deletion if Zapier did not provide a
    # recognizable successful response.
    # ============================================================

    return {
        "status": "ERROR",
        "app": "google_sheets",
        "action": "delete_spreadsheet_rows",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_name": spreadsheet_name,
        "worksheet": worksheet,
        "rows": rows,
        "message": (
            f"The rows '{rows}' could not be confirmed "
            f"as deleted from worksheet "
            f"'{worksheet}'."
        ),
        "raw_result": result_data
    }

async def _delete_google_sheet_rows(user_id, mcp_url, params):
    """
    Delete Google Sheets row(s).

    Supports:

    1. Explicit rows

        {
            "spreadsheet_name": "Sales Report",
            "rows": "5"
        }

    2. Multiple rows

        {
            "spreadsheet_name": "Sales Report",
            "rows": "2,5,7"
        }

    3. Range

        {
            "spreadsheet_name": "Sales Report",
            "rows": "2-5"
        }

    4. Condition

        {
            "spreadsheet_name": "Sales Report",
            "condition": {
                "column": "Customer",
                "operator": "=",
                "value": "ABC Traders"
            }
        }

    Worksheet is OPTIONAL.

    If worksheet is omitted:
        first worksheet is used.

    IMPORTANT:

    - Condition is evaluated locally.
    - Spreadsheet is resolved once.
    - Worksheet is resolved once.
    - Condition read is performed once.
    - Actual Zapier delete action is performed exactly once.
    - This function never recursively calls itself.
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_id = (
        params.get("spreadsheet_id")
        or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name")
        or ""
    ).strip()

    requested_worksheet = (
        params.get("worksheet")
        or ""
    ).strip()

    rows = params.get(
        "rows"
    )

    condition = params.get(
        "condition"
    )

    print("=" * 70)
    print("GOOGLE SHEETS DELETE ROWS")
    print(
        "SPREADSHEET NAME :",
        spreadsheet_name
    )
    print(
        "SPREADSHEET ID   :",
        spreadsheet_id
    )
    print(
        "WORKSHEET        :",
        requested_worksheet
        or "(DEFAULT/FIRST)"
    )
    print(
        "ROWS             :",
        rows
    )
    print(
        "CONDITION        :",
        condition
    )
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if (
        not spreadsheet_id
        and not spreadsheet_name
    ):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    if (
        rows is None
        and condition is None
    ):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "message": (
                "Please provide either rows or a "
                "condition to determine which rows "
                "should be deleted."
            )
        }

    if (
        rows is not None
        and condition is not None
    ):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "message": (
                "Please provide either rows or "
                "condition, not both."
            )
        }

    # ============================================================
    # STEP 1
    # RESOLVE SPREADSHEET
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            f"resolving spreadsheet '{spreadsheet_name}'"
        )

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name=(
                    "google_sheets_delete_spreadsheet_row_s"
                ),
                enum_property_name="spreadsheet"
            )
        )

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            f"resolved spreadsheet ID={spreadsheet_id}"
        )

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f"Google Spreadsheet "
                f"'{spreadsheet_name}' "
                "could not be found."
            )
        }

    # ============================================================
    # STEP 2
    # RESOLVE WORKSHEET
    #
    # IMPORTANT:
    #
    # If omitted, FIRST worksheet is selected.
    # ============================================================

    print(
        "GOOGLE SHEETS DELETE ROWS: "
        "resolving worksheet"
    )

    # # # worksheet_result = (
    # # #     await _resolve_google_worksheet_delete_row(
    # # #         user_id=user_id,
    # # #         mcp_url=mcp_url,
    # # #         spreadsheet_id=spreadsheet_id,
    # # #         worksheet_name=requested_worksheet,
    # # #         tool_name=(
    # # #             "google_sheets_delete_spreadsheet_row_s"
    # # #         )
    # # #     )
    # # # )

    worksheet_result = await _resolve_google_worksheet(
        user_id=user_id,
        mcp_url=mcp_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=requested_worksheet,
        tool_name=(
            "google_sheets_get_many_spreadsheet_rows_advanced"
        )
    )

    print(
        "GOOGLE SHEETS DELETE ROWS "
        "WORKSHEET RESOLVE:",
        worksheet_result
    )

    if (
        not isinstance(
            worksheet_result,
            dict
        )
    ):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "Invalid worksheet resolution result."
            )
        }

    worksheet_status = (
        worksheet_result.get(
            "status"
        )
    )

    if worksheet_status == "ERROR":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": worksheet_result.get(
                "message",
                "Unable to determine worksheet."
            ),
            "error": worksheet_result.get(
                "error"
            )
        }

    if worksheet_status == "NOT_FOUND":

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "No worksheet was found "
                "in the spreadsheet."
            )
        }

    if worksheet_status == "MULTIPLE":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "Unable to determine the worksheet."
            ),
            "worksheets": (
                worksheet_result.get(
                    "worksheets",
                    []
                )
            )
        }

    worksheet = str(
        worksheet_result.get(
            "worksheet"
        )
        or ""
    ).strip()

    worksheet_name = str(
        worksheet_result.get(
            "worksheet_name"
        )
        or requested_worksheet
        or ""
    ).strip()

    if not worksheet:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "Unable to determine the worksheet value."
            )
        }

    print(
        "GOOGLE SHEETS DELETE ROWS:"
    )
    print(
        "  worksheet value =",
        worksheet
    )
    print(
        "  worksheet name  =",
        worksheet_name
    )

    # ============================================================
    # STEP 3
    # DETERMINE ROWS
    # ============================================================

    rows_to_delete = []

    # ============================================================
    # CASE A: CONDITION
    # ============================================================

    if condition is not None:

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            "processing condition"
        )

        if not isinstance(
            condition,
            dict
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "message": (
                    "Condition must be an object "
                    "containing column, operator "
                    "and value."
                )
            }

        condition_column = str(
            condition.get(
                "column"
            )
            or ""
        ).strip()

        condition_operator = str(
            condition.get(
                "operator"
            )
            or "="
        ).strip()

        condition_value = condition.get(
            "value"
        )

        if not condition_column:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "message": (
                    "Condition column is required."
                )
            }

        if condition_value is None:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "message": (
                    "Condition value is required."
                )
            }

        # --------------------------------------------------------
        # READ SHEET EXACTLY ONCE
        # --------------------------------------------------------

        condition_read = (
            await _read_google_rows_for_condition(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=spreadsheet_id,
                worksheet=worksheet
            )
        )

        if (
            condition_read.get(
                "status"
            )
            == "ERROR"
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "message": (
                    "Unable to read spreadsheet "
                    "rows for condition matching."
                ),
                "error": condition_read.get(
                    "error"
                )
            }

        data_rows = (
            condition_read.get(
                "rows",
                []
            )
        )

        header_map = (
            condition_read.get(
                "headers",
                {}
            )
        )

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            f"condition read returned "
            f"{len(data_rows)} data rows"
        )

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            "header map =",
            header_map
        )

        # --------------------------------------------------------
        # FIND MATCHING ROWS
        # --------------------------------------------------------

        for row_data in data_rows:

            if not isinstance(
                row_data,
                dict
            ):
                continue

            # ----------------------------------------------------
            # IMPORTANT:
            #
            # Support both:
            #
            #     row
            #
            # and:
            #
            #     row_number
            #
            # from Zapier.
            # ----------------------------------------------------

            row_number = (
                row_data.get(
                    "row"
                )
                or row_data.get(
                    "row_number"
                )
                or row_data.get(
                    "id"
                )
            )

            try:

                row_number = int(
                    row_number
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if row_number <= 1:
                continue

            actual_value = (
                _get_condition_column_value(
                    row=row_data,
                    requested_column=condition_column,
                    header_map=header_map
                )
            )

            print(
                "GOOGLE SHEETS CONDITION CHECK:",
                "row=",
                row_number,
                "column=",
                condition_column,
                "actual=",
                actual_value,
                "operator=",
                condition_operator,
                "expected=",
                condition_value
            )

            if _evaluate_google_sheet_condition(
                actual_value=actual_value,
                operator=condition_operator,
                expected_value=condition_value
            ):

                rows_to_delete.append(
                    row_number
                )

        rows_to_delete = sorted(
            set(
                rows_to_delete
            )
        )

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            f"condition matched rows="
            f"{rows_to_delete}"
        )

        # --------------------------------------------------------
        # NOTHING MATCHED
        # --------------------------------------------------------

        if not rows_to_delete:

            return {
                "status": "NOT_FOUND",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "condition": condition,
                "rows": [],
                "message": (
                    f"No rows matched the condition "
                    f"'{condition_column} "
                    f"{condition_operator} "
                    f"{condition_value}'."
                )
            }

    # ============================================================
    # CASE B: EXPLICIT ROWS
    # ============================================================

    else:

        print(
            "GOOGLE SHEETS DELETE ROWS: "
            "processing explicit row specification"
        )

        try:

            rows_to_delete = (
                _parse_google_sheet_rows(
                    rows
                )
            )

        except ValueError as e:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "message": str(e)
            }

        if not rows_to_delete:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "message": (
                    "No valid row numbers were provided."
                )
            }

    # ============================================================
    # STEP 4
    # COMPRESS ROWS
    #
    # Example:
    #
    # [2, 5, 6, 7]
    #
    # -> "2,5-7"
    # ============================================================

    rows_to_delete = sorted(
        set(
            int(row)
            for row in rows_to_delete
        )
    )

    row_specification = (
        _compress_google_sheet_rows(
            rows_to_delete
        )
    )

    print(
        "GOOGLE SHEETS DELETE ROWS:"
    )
    print(
        "  spreadsheet ID   =",
        spreadsheet_id
    )
    print(
        "  worksheet        =",
        worksheet
    )
    print(
        "  worksheet name   =",
        worksheet_name
    )
    print(
        "  rows             =",
        rows_to_delete
    )
    print(
        "  row specification =",
        row_specification
    )

    # ============================================================
    # STEP 5
    # ACTUAL ZAPIER DELETE
    #
    # THIS IS THE ONLY DELETE ACTION.
    #
    # EXACTLY ONE CALL.
    # ============================================================

    try:

        delete_result = (
            await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name=(
                    "google_sheets_delete_spreadsheet_row_s"
                ),
                params={
                    "spreadsheet": spreadsheet_id,
                    "worksheet": worksheet,
                    "rows": row_specification,
                    "output_hint": (
                        "Confirm that the specified "
                        "spreadsheet rows were deleted "
                        "successfully."
                    )
                }
            )
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS DELETE ROWS EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet_name,
            "rows": rows_to_delete,
            "message": (
                "Unable to delete the Google "
                "Sheets rows."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS DELETE ROWS RAW RESULT ==="
    )
    print(delete_result)
    print(
        "=== END GOOGLE SHEETS DELETE ROWS RAW RESULT ==="
    )

    # ============================================================
    # STEP 6
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        delete_result
    )

    if error:

        print(
            "GOOGLE SHEETS DELETE ROWS ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "delete_spreadsheet_rows",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet_name,
            "rows": rows_to_delete,
            "message": (
                "The Google Sheets rows "
                "could not be deleted."
            ),
            "error": error
        }

    # ============================================================
    # STEP 7
    # PARSE RESULT
    # ============================================================

    result_data = (
        _parse_zapier_json_result(
            delete_result
        )
    )

    print(
        "GOOGLE SHEETS DELETE ROWS "
        "PARSED RESULT:",
        result_data
    )

    # ============================================================
    # EXPLICIT MCP ERROR
    # ============================================================

    if isinstance(
        result_data,
        dict
    ):

        if result_data.get(
            "isError"
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "delete_spreadsheet_rows",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet_name,
                "rows": rows_to_delete,
                "message": (
                    "The Google Sheets rows "
                    "could not be deleted."
                ),
                "error": (
                    result_data.get(
                        "error"
                    )
                    or
                    "Google Sheets delete operation failed."
                )
            }

    # ============================================================
    # SUCCESS
    #
    # The delete tool returned without an error.
    #
    # Do NOT call another Zapier action.
    # ============================================================

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "delete_spreadsheet_rows",
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_name": spreadsheet_name,
        "worksheet": worksheet_name,
        "rows": rows_to_delete,
        "row_specification": row_specification,
        "condition": condition,
        "message": (
            f"Successfully deleted "
            f"{len(rows_to_delete)} row"
            f"{'' if len(rows_to_delete) == 1 else 's'} "
            f"from worksheet '{worksheet_name}'."
        )
    }

async def _read_google_spreadsheet(user_id, mcp_url, params):

    manager = get_zapier_manager()

    spreadsheet_id = (params.get("spreadsheet_id") or "").strip()

    spreadsheet_name = (params.get("spreadsheet_name") or "").strip()

    worksheet = (params.get("worksheet") or "").strip()

    # ------------------------------------------------------------
    # Requested starting row
    # ------------------------------------------------------------

    first_row = params.get("first_row", 2)

    try:
        first_row = int(first_row)
    except Exception:
        first_row = 2

    if first_row < 1:
        first_row = 1

    # ------------------------------------------------------------
    # Requested number of rows
    #
    # None / omitted means read until no more rows.
    # ------------------------------------------------------------

    requested_row_count = params.get("row_count")

    if requested_row_count is not None:

        try:
            requested_row_count = int(requested_row_count)
        except Exception:
            requested_row_count = None

        if requested_row_count is not None:
            requested_row_count = max(0, requested_row_count)

    # ------------------------------------------------------------
    # Batch size
    # ------------------------------------------------------------

    batch_size = params.get("batch_size", 1500)

    try:
        batch_size = int(batch_size)
    except Exception:
        batch_size = 1500

    # Zapier maximum
    batch_size = max(1, min(batch_size, 1500))

    print("=" * 60)
    print("GOOGLE SHEETS READ")
    print(f"SPREADSHEET NAME : {spreadsheet_name}")
    print(f"SPREADSHEET ID   : {spreadsheet_id}")
    print(f"WORKSHEET        : {worksheet}")
    print(f"FIRST ROW        : {first_row}")
    print(f"ROW COUNT        : {requested_row_count}")
    print(f"BATCH SIZE       : {batch_size}")
    print("=" * 60)

    # ============================================================
    # STEP 1
    # Resolve spreadsheet ID
    # ============================================================

    if not spreadsheet_id:

        if not spreadsheet_name:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "read_spreadsheet",
                "message": (
                    "Please provide spreadsheet_name "
                    "or spreadsheet_id."
                )
            }

        print(
            "GOOGLE SHEETS: resolving spreadsheet "
            f"'{spreadsheet_name}'"
        )

        # Use your existing spreadsheet-name resolver here.
        spreadsheet_id = await _resolve_google_spreadsheet_id(
            user_id=user_id,
            mcp_url=mcp_url,
            spreadsheet_id=spreadsheet_id,
            spreadsheet_name=spreadsheet_name,
            tool_name="google_sheets_get_many_spreadsheet_rows_advanced",
            enum_property_name="spreadsheet_id"
        )

        print(
            "GOOGLE SHEETS RESOLVED ID:",
            spreadsheet_id
        )

        if not spreadsheet_id:

            return {
                "status": "NOT_FOUND",
                "app": "google_sheets",
                "action": "read_spreadsheet",
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    f"Spreadsheet '{spreadsheet_name}' "
                    "could not be found."
                )
            }

    # ============================================================
    # STEP 2
    # Get Worksheet
    # ============================================================

    worksheet_result = await _resolve_google_worksheet(
        user_id=user_id,
        mcp_url=mcp_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet
    )

    # ============================================================
    # WORKSHEET RESOLUTION RESULT
    # ============================================================

    if worksheet_result["status"] == "ERROR":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "read_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "message": worksheet_result.get(
                "message",
                "Unable to determine the worksheet."
            ),
            "error": worksheet_result.get("error")
        }


    if worksheet_result["status"] == "NOT_FOUND":

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "read_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "message": worksheet_result.get(
                "message",
                "No worksheet was found."
            )
        }


    if worksheet_result["status"] == "MULTIPLE":

        worksheets = worksheet_result.get(
            "worksheets",
            []
        )

        return {
            "status": "MULTIPLE_WORKSHEETS",
            "app": "google_sheets",
            "action": "read_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheets": worksheets,
            "message": (
                f'The Google Sheet "{spreadsheet_name}" '
                "has multiple worksheets. "
                "Please specify which worksheet you "
                "would like me to read."
            )
        }


    # ============================================================
    # Worksheet successfully resolved
    # ============================================================

    worksheet = worksheet_result["worksheet"]

    print(
        "GOOGLE SHEETS RESOLVED WORKSHEET: "
        f"{worksheet}"
    )

    if not worksheet:
        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "read_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "message": (
                "Unable to determine the worksheet "
                "for the Google Spreadsheet."
            )
        }

    # ============================================================
    # STEP 3
    # Read rows in batches
    # ============================================================

    all_rows = []

    current_row = first_row

    remaining = requested_row_count

    batch_number = 0

    while True:

        batch_number += 1

        # --------------------------------------------------------
        # Determine this batch size
        # --------------------------------------------------------

        if remaining is None:

            current_batch_size = batch_size

        else:

            if remaining <= 0:
                break

            current_batch_size = min(
                batch_size,
                remaining
            )

        print(
            "=" * 60
        )

        print(
            f"GOOGLE SHEETS BATCH #{batch_number}"
        )

        print(
            f"START ROW : {current_row}"
        )

        print(
            f"BATCH SIZE: {current_batch_size}"
        )

        # --------------------------------------------------------
        # Zapier call
        # --------------------------------------------------------

        try:

            result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name=("google_sheets_get_many_spreadsheet_rows_advanced"),
                params={
                    "spreadsheet": spreadsheet_id,
                    "worksheet": worksheet,
                    "first_row": current_row,
                    "row_count": current_batch_size,
                    "range": "A:Z",
                    "output_format": "all",
                    "output_hint": "Return all spreadsheet rows and columns with their header names."
                }
            )

            print("")
            print("=== GOOGLE SHEETS BATCH RAW RESULT ===")
            print(result)
            print("=== END GOOGLE SHEETS BATCH RAW RESULT ===")
            print("")

        except Exception as e:

            print(
                "GOOGLE SHEETS BATCH ERROR:",
                e
            )

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "read_spreadsheet",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "message": (
                    f"Error reading batch "
                    f"{batch_number}."
                ),
                "error": str(e),
                "rows_read": len(all_rows)
            }

        # --------------------------------------------------------
        # Check Zapier error
        # --------------------------------------------------------

        error = extract_zapier_error(result)

        if error:

            print(
                "GOOGLE SHEETS BATCH ZAPIER ERROR:",
                error
            )

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "read_spreadsheet",
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "message": (
                    f"Zapier failed while reading "
                    f"batch {batch_number}."
                ),
                "error": error,
                "rows_read": len(all_rows)
            }

        # --------------------------------------------------------
        # Extract rows
        # --------------------------------------------------------

        batch_rows = extract_google_sheet_rows(
            result
        )

        print(
            f"GOOGLE SHEETS BATCH #{batch_number} "
            f"RETURNED {len(batch_rows)} ROWS"
        )

        # --------------------------------------------------------
        # Add rows
        # --------------------------------------------------------

        all_rows.extend(batch_rows)

        # --------------------------------------------------------
        # No more rows
        #
        # If fewer rows came back than requested,
        # we reached the end.
        # --------------------------------------------------------

        if len(batch_rows) < current_batch_size:

            print(
                "GOOGLE SHEETS: reached end of data."
            )

            break

        # --------------------------------------------------------
        # Requested count reached
        # --------------------------------------------------------

        if remaining is not None:

            remaining -= len(batch_rows)

            if remaining <= 0:

                print(
                    "GOOGLE SHEETS: requested row count reached."
                )

                break

        # --------------------------------------------------------
        # Move to next batch
        # --------------------------------------------------------

        current_row += len(batch_rows)

    # ============================================================
    # STEP 3
    # Return combined result
    # ============================================================

    print("=" * 60)

    print(
        "GOOGLE SHEETS TOTAL ROWS:",
        len(all_rows)
    )

    print("=" * 60)

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "read_spreadsheet",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet,
        "first_row": first_row,
        "rows_requested": requested_row_count,
        "batch_size": batch_size,
        "rows_read": len(all_rows),
        "data": all_rows
    }

def build_google_sheet_dynamic_properties(schema_result,row_data):
    """
    Convert AI row data using column/header names into
    Zapier dynamic_properties.

    Example schema:

    {
        "properties": {
            "COL$A": {"description": "Name"},
            "COL$B": {"description": "email"},
            "COL$C": {"description": "PhoneNo"}
        }
    }

    AI row:

    {
        "Name": "John",
        "email": "john@gmail.com",
        "PhoneNo": "9999999999"
    }

    Result:

    {
        "COL$A": "John",
        "COL$B": "john@gmail.com",
        "COL$C": "9999999999"
    }
    """

    if not isinstance(row_data, dict):
        return None, {
            "status": "ERROR",
            "message": "Row data must be an object."
        }

    data = schema_result

    # ------------------------------------------------------------
    # Extract MCP text block
    # ------------------------------------------------------------

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                data = json.loads(text)
                break
            except Exception:
                continue

    if not isinstance(data, dict):

        return None, {
            "status": "ERROR",
            "message": (
                "Invalid dynamic property schema returned "
                "by Zapier."
            )
        }

    schema = data.get("schema")

    if not isinstance(schema, dict):

        return None, {
            "status": "ERROR",
            "message": (
                "Zapier dynamic property schema "
                "does not contain a schema object."
            )
        }

    properties = schema.get("properties")

    if not isinstance(properties, dict):

        return None, {
            "status": "ERROR",
            "message": (
                "Zapier dynamic property schema "
                "does not contain spreadsheet columns."
            )
        }

    # ------------------------------------------------------------
    # Build normalized header lookup
    # ------------------------------------------------------------

    header_lookup = {}

    for property_name, property_info in properties.items():

        if not isinstance(property_info, dict):
            continue

        description = (
            property_info.get("description")
            or ""
        ).strip()

        if description:

            header_lookup[
                description.casefold()
            ] = property_name

    print(
        "GOOGLE SHEETS HEADER LOOKUP:",
        header_lookup
    )

    # ------------------------------------------------------------
    # Build dynamic properties
    # ------------------------------------------------------------

    dynamic_properties = {}

    unknown_columns = []

    for column_name, value in row_data.items():

        normalized_column = str(
            column_name
        ).strip().casefold()

        property_name = header_lookup.get(
            normalized_column
        )

        if not property_name:

            unknown_columns.append(
                column_name
            )

            continue

        dynamic_properties[property_name] = (
            "" if value is None else str(value)
        )

    # ------------------------------------------------------------
    # Unknown columns
    # ------------------------------------------------------------

    if unknown_columns:

        return None, {
            "status": "ERROR",
            "message": (
                "The row contains columns that do not "
                "exist in the spreadsheet."
            ),
            "unknown_columns": unknown_columns,
            "available_columns": list(
                header_lookup.keys()
            )
        }

    return dynamic_properties, None

def _normalize_google_sheet_column_name(value):
    """
    Normalize Google Sheets column/header names so that
    human variations map to the same column.

    Examples:

        Invoice No.
        Invoice no
        invoice no.
        INVOICE NO
        Invoice_No
        Invoice-No

    all normalize to the same value.

    Also normalizes Zapier/internal column keys:

        COL$B
        COL_B

    to the same canonical form.
    """

    if value is None:
        return ""

    value = str(value).strip().casefold()

    # Normalize Zapier column-key variants.
    value = value.replace("$", "_")

    # Normalize punctuation/separators.
    value = re.sub(r"[^a-z0-9]+", " ", value)

    # Collapse whitespace.
    value = re.sub(r"\s+", " ", value).strip()

    return value

def build_google_sheet_header_lookup(schema_result):
    """
    Build a mapping between human-readable spreadsheet
    column names and Zapier column keys.

    Example schema:

    {
        "schema": {
            "properties": {
                "COL$A": {
                    "description": "Date"
                },
                "COL$B": {
                    "description": "Invoice No."
                },
                "COL$H": {
                    "description": "Discount"
                }
            }
        }
    }

    Result:

    {
        "date": "COL$A",
        "invoice no": "COL$B",
        "discount": "COL$H"
    }
    """

    data = schema_result

    # ------------------------------------------------------------
    # Extract MCP text block
    # ------------------------------------------------------------

    if isinstance(data, list):

        for block in data:

            if not isinstance(block, dict):
                continue

            text = block.get("text")

            if not text:
                continue

            try:
                data = json.loads(text)
                break

            except Exception:
                continue

    if not isinstance(data, dict):
        return {}

    # ------------------------------------------------------------
    # Extract schema
    # ------------------------------------------------------------

    schema = data.get("schema")

    if not isinstance(schema, dict):
        return {}

    properties = schema.get("properties")

    if not isinstance(properties, dict):
        return {}

    # ------------------------------------------------------------
    # Build normalized lookup
    # ------------------------------------------------------------

    header_lookup = {}

    for property_name, property_info in properties.items():

        if not isinstance(property_info, dict):
            continue

        description = (
            property_info.get("description")
            or ""
        ).strip()

        if not description:
            continue

        normalized_description = (
            _normalize_google_sheet_column_name(
                description
            )
        )

        if normalized_description:
            header_lookup[
                normalized_description
            ] = property_name

        # Also allow the internal Zapier column name itself.
        normalized_property = (
            _normalize_google_sheet_column_name(
                property_name
            )
        )

        if normalized_property:
            header_lookup[
                normalized_property
            ] = property_name

    print(
        "GOOGLE SHEETS HEADER LOOKUP:",
        header_lookup
    )

    return header_lookup

async def _create_google_spreadsheet(user_id, mcp_url, params):
    """
    Create a new Google Spreadsheet with header columns only.

    Example:

        {
            "spreadsheet_name": "Employee",
            "columns": [
                "EmpId",
                "Name",
                "Salary"
            ]
        }

    This operation ONLY creates the spreadsheet and header row.

    It does NOT create a data row.

    The actual Zapier operation is:

        google_sheets_create_spreadsheet
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_name = (
        params.get("spreadsheet_name")
        or params.get("title")
        or ""
    ).strip()

    columns = (
        params.get("columns")
        or params.get("headers")
        or []
    )

    print("=" * 70)
    print("GOOGLE SHEETS CREATE SPREADSHEET")
    print("SPREADSHEET NAME :", spreadsheet_name)
    print("COLUMNS          :", columns)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not spreadsheet_name:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "create_spreadsheet",
            "message": (
                "Please provide a spreadsheet_name."
            )
        }

    # ------------------------------------------------------------
    # Normalize columns
    # ------------------------------------------------------------

    if isinstance(columns, str):

        # Support:

        # "EmpId, Name, Salary"

        columns = [
            item.strip()
            for item in columns.split(",")
            if item.strip()
        ]

    if not isinstance(columns, list):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "create_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "columns must be a list of column names."
            )
        }

    # ------------------------------------------------------------
    # Clean column names
    # ------------------------------------------------------------

    headers = []

    for column in columns:

        if column is None:
            continue

        column_name = str(column).strip()

        if not column_name:
            continue

        headers.append(column_name)

    # ------------------------------------------------------------
    # At least one column is required
    # ------------------------------------------------------------

    if not headers:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "create_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                "Please provide at least one column name."
            )
        }

    # ------------------------------------------------------------
    # Remove duplicate column names while preserving order.
    #
    # Example:
    #
    # ["EmpId", "Name", "Salary", "Name"]
    #
    # becomes:
    #
    # ["EmpId", "Name", "Salary"]
    # ------------------------------------------------------------

    unique_headers = []

    seen_headers = set()

    for header in headers:

        normalized = header.casefold()

        if normalized in seen_headers:
            continue

        seen_headers.add(normalized)

        unique_headers.append(header)

    headers = unique_headers

    print(
        "GOOGLE SHEETS FINAL HEADERS:",
        headers
    )

    # ============================================================
    # CREATE SPREADSHEET
    # ============================================================

    try:

        create_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_sheets_create_spreadsheet",
            params={
                "title": spreadsheet_name,
                "headers": headers,
                "output_hint": (
                    "Return only confirmation that the "
                    "Google Spreadsheet was created successfully, "
                    "including the spreadsheet ID and name. "
                    "Do not create or append any data rows."
                )
            }
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS CREATE EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "create_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "headers": headers,
            "message": (
                "Unable to create the Google Spreadsheet."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS CREATE RAW RESULT ==="
    )
    print(create_result)
    print(
        "=== END GOOGLE SHEETS CREATE RAW RESULT ==="
    )

    # ============================================================
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        create_result
    )

    if error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "create_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "headers": headers,
            "message": (
                "Google Spreadsheet creation failed."
            ),
            "error": error
        }

    # ============================================================
    # EXTRACT SPREADSHEET ID
    # ============================================================

    spreadsheet_id = extract_google_spreadsheet_id(
        create_result
    )

    # ============================================================
    # SUCCESS
    # ============================================================

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "create_spreadsheet",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "headers": headers,
        "message": (
            f"Google Spreadsheet '{spreadsheet_name}' "
            "was created successfully with the specified "
            "columns."
        )
    }

async def _append_google_sheet_row(user_id, mcp_url, params):
    """
    Append a row to a Google Spreadsheet.

    Behavior:

    1. Resolve spreadsheet by ID/name.
    2. Create spreadsheet if it does not exist.
    3. Resolve worksheet.
    4. Create worksheet if it does not exist.
    5. Resolve dynamic_properties schema.
    6. Append the row.
    """

    manager = get_zapier_manager()

    spreadsheet_id = (
        params.get("spreadsheet_id") or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name") or ""
    ).strip()

    worksheet = (
        params.get("worksheet") or ""
    ).strip()
    
    row_data = params.get("row") or {}

    print("=" * 60)
    print("GOOGLE SHEETS APPEND ROW")
    print(f"SPREADSHEET NAME : {spreadsheet_name}")
    print(f"SPREADSHEET ID   : {spreadsheet_id}")
    print(f"WORKSHEET        : {worksheet}")
    print(f"ROW DATA         : {row_data}")
    print("=" * 60)

    # ============================================================
    # Validate
    # ============================================================

    if not spreadsheet_id and not spreadsheet_name:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    if not isinstance(row_data, dict) or not row_data:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "message": (
                "Please provide row data as a non-empty object."
            )
        }

    # ============================================================
    # STEP 1
    # Resolve spreadsheet
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS: resolving spreadsheet "
            f"'{spreadsheet_name}'"
        )

        spreadsheet_id = await _resolve_google_spreadsheet_id(
            user_id=user_id,
            mcp_url=mcp_url,
            spreadsheet_id=None,
            spreadsheet_name=spreadsheet_name,
            tool_name="google_sheets_create_spreadsheet_row",
            enum_property_name="spreadsheet"
        )

        print(
            "GOOGLE SHEETS RESOLVED ID:",
            spreadsheet_id
        )

    # ============================================================
    # STEP 2
    # Spreadsheet does not exist -> CREATE
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS: spreadsheet does not exist."
        )

        print(
            f"GOOGLE SHEETS: creating spreadsheet "
            f"'{spreadsheet_name}'"
        )

        headers = [
            str(key)
            for key in row_data.keys()
        ]

        try:

            create_result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name="google_sheets_create_spreadsheet",
                params={
                    "title": spreadsheet_name,
                    "headers": headers,
                    "output_hint": (
                        "Return the newly created spreadsheet "
                        "ID and spreadsheet name."
                    )
                }
            )

            print(
                "=== GOOGLE SHEETS CREATE RESULT ==="
            )
            print(create_result)

        except Exception as e:

            print(
                "GOOGLE SHEETS CREATE ERROR:",
                e
            )

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "append_row",
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    "Unable to create the Google Spreadsheet."
                ),
                "error": str(e)
            }

        error = extract_zapier_error(
            create_result
        )

        if error:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "append_row",
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    "Google Spreadsheet creation failed."
                ),
                "error": error
            }

        spreadsheet_id = extract_google_spreadsheet_id(
            create_result
        )

        print(
            "GOOGLE SHEETS CREATED ID:",
            spreadsheet_id
        )

        if not spreadsheet_id:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "append_row",
                "spreadsheet_name": spreadsheet_name,
                "message": (
                    "Spreadsheet was created, but "
                    "no spreadsheet ID was returned."
                ),
                "data": create_result
            }

    # ============================================================
    # STEP 3
    # Resolve worksheet
    # ============================================================

    worksheet_result = await _resolve_google_worksheet(
        user_id=user_id,
        mcp_url=mcp_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet
    )

    print(
        "GOOGLE SHEETS WORKSHEET RESULT:",
        worksheet_result
    )

    # ============================================================
    # STEP 4
    # Worksheet does not exist
    # ============================================================

    if worksheet_result.get("status") == "NOT_FOUND":

        # If user didn't specify worksheet, use "Sheet1"
        if not worksheet:

            worksheet = "Sheet1"

        print(
            "GOOGLE SHEETS: worksheet does not exist."
        )

        print(
            f"GOOGLE SHEETS: creating worksheet "
            f"'{worksheet}'"
        )

        headers = [
            str(key)
            for key in row_data.keys()
        ]

        try:

            create_worksheet_result = (
                await manager.execute_tool(
                    user_id=user_id,
                    mcp_url=mcp_url,
                    tool_name=(
                        "google_sheets_create_worksheet"
                    ),
                    params={
                        "spreadsheet": spreadsheet_id,
                        "title": worksheet,
                        "headers": headers,
                        "output_hint": (
                            "Return confirmation that the "
                            "worksheet was created successfully."
                        )
                    }
                )
            )

            print(
                "=== GOOGLE SHEETS WORKSHEET CREATE RESULT ==="
            )
            print(create_worksheet_result)

        except Exception as e:

            print(
                "GOOGLE SHEETS WORKSHEET CREATE ERROR:",
                e
            )

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "append_row",
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "message": (
                    "Unable to create the worksheet."
                ),
                "error": str(e)
            }

        error = extract_zapier_error(
            create_worksheet_result
        )

        if error:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "append_row",
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "message": (
                    "Worksheet creation failed."
                ),
                "error": error
            }

    elif worksheet_result.get("status") == "MULTIPLE":

        return {
            "status": "MULTIPLE_WORKSHEETS",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheets": worksheet_result.get(
                "worksheets",
                []
            ),
            "message": (
                f'The Google Sheet "{spreadsheet_name}" '
                "has multiple worksheets. "
                "Please specify which worksheet "
                "you want to append to."
            )
        }

    elif worksheet_result.get("status") == "ERROR":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": worksheet_result.get(
                "message",
                "Unable to determine worksheet."
            ),
            "error": worksheet_result.get("error")
        }

    else:

        # Existing worksheet
        worksheet = (
            worksheet_result.get("worksheet")
            or worksheet
        )

    # ============================================================
    # STEP 5
    # Resolve dynamic_properties schema
    # ============================================================

    print(
        "=== GOOGLE SHEETS DYNAMIC PROPERTY SCHEMA ==="
    )

    try:

        schema_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="get_dynamic_properties_schema",
            params={
                "tool_name": (
                    "google_sheets_create_spreadsheet_row"
                ),
                "tool_arguments": {
                    "spreadsheet": spreadsheet_id,
                    "worksheet": worksheet,
                    "dynamic_properties": {}
                }
            }
        )

        print(
            "=== GOOGLE SHEETS DYNAMIC SCHEMA RESULT ==="
        )
        print(schema_result)

    except Exception as e:

        print(
            "GOOGLE SHEETS DYNAMIC SCHEMA ERROR:",
            e
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Unable to determine spreadsheet columns."
            ),
            "error": str(e)
        }

    schema_error = extract_zapier_error(
        schema_result
    )

    if schema_error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Unable to determine spreadsheet columns."
            ),
            "error": schema_error
        }

    # ============================================================
    # STEP 6
    # Build dynamic_properties from Zapier schema
    # ============================================================

    dynamic_properties, dynamic_property_error = (
        build_google_sheet_dynamic_properties(
            schema_result,
            row_data
        )
    )

    if dynamic_property_error:

        print(
            "GOOGLE SHEETS DYNAMIC PROPERTY ERROR:",
            dynamic_property_error
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": dynamic_property_error.get(
                "message",
                "Unable to map spreadsheet columns."
            ),
            "error": dynamic_property_error
        }

    print(
        "GOOGLE SHEETS DYNAMIC PROPERTIES:",
        dynamic_properties
    )

    # ============================================================
    # STEP 7
    # Create row
    # ============================================================

    try:

        append_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=(
                "google_sheets_create_spreadsheet_row"
            ),
            params={
                "spreadsheet": spreadsheet_id,
                "worksheet": worksheet,
                "dynamic_properties": dynamic_properties,
                "output_hint": (
                    "Return confirmation that the row was "
                    "successfully added, including spreadsheet "
                    "name, worksheet and row data."
                )
            }
        )

        print(
            "=== GOOGLE SHEETS APPEND RAW RESULT ==="
        )
        print(append_result)

    except Exception as e:

        print(
            "GOOGLE SHEETS APPEND ERROR:",
            e
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Unable to append row to the Google Sheet."
            ),
            "error": str(e)
        }

    # ============================================================
    # STEP 8
    # Check Zapier error
    # ============================================================

    error = extract_zapier_error(
        append_result
    )

    if error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "append_row",
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "The row could not be added."
            ),
            "error": error
        }

    # ============================================================
    # SUCCESS
    # ============================================================

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "append_row",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet,
        "message": (
            f"Row successfully appended to "
            f"'{spreadsheet_name}'"
        ),
        "data": row_data
    }


    """
    Update an existing Google Sheets row.

    Supports:

    1. Explicit row number

        {
            "row_number": 7,
            "updates": {
                "Salary": 50000
            }
        }

    2. Find row by column/value

        {
            "find": {
                "column": "Invoice No",
                "value": "INV-1001"
            },
            "updates": {
                "Discount": 3000
            }
        }

    3. Find row + old-value safety condition

        {
            "find": {
                "column": "Name",
                "value": "Rahul"
            },
            "condition": {
                "column": "Salary",
                "value": 45000
            },
            "updates": {
                "Salary": 50000
            }
        }

    Important:

    - Human column names are accepted.
    - Column matching is case-insensitive.
    - Punctuation differences are ignored.
      Example:
          "Invoice no"
          "Invoice No."
          "invoice no."
          "INVOICE NO"
      all resolve to the same spreadsheet column.
    - The AI does NOT need to know COL$A/COL$B/etc.
    - Zapier dynamic properties are generated internally.
    - Exactly one matching row is required.
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_id = (
        params.get("spreadsheet_id") or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name") or ""
    ).strip()

    worksheet = (
        params.get("worksheet") or ""
    ).strip()

    row_number = params.get("row_number")

    find = params.get("find") or {}

    condition = params.get("condition") or {}

    updates = params.get("updates") or {}

    print("=" * 60)
    print("GOOGLE SHEETS UPDATE ROW")
    print("SPREADSHEET :", spreadsheet_name)
    print("WORKSHEET   :", worksheet)
    print("ROW         :", row_number)
    print("FIND        :", find)
    print("CONDITION   :", condition)
    print("UPDATES     :", updates)
    print("=" * 60)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not spreadsheet_id and not spreadsheet_name:
        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    if not isinstance(updates, dict) or not updates:
        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": (
                "Please provide at least one value "
                "to update."
            )
        }

    # ============================================================
    # INTERNAL COLUMN NORMALIZATION
    # ============================================================
    #
    # This fixes:
    #
    # "Invoice no"
    # "Invoice No."
    # "invoice no."
    # "INVOICE NO"
    #
    # -> same normalized key
    #
    # It also handles:
    #
    # "Payment Status"
    # "payment-status"
    # "Payment_Status"
    #
    # -> same normalized key
    #
    # The AI therefore does not have to reproduce the exact
    # punctuation/capitalization of the Google Sheet header.
    # ============================================================

    def normalize_column_name(value):
        if value is None:
            return ""

        value = str(value).strip().casefold()

        # Keep only letters and numbers.
        # This intentionally removes:
        # spaces, ".", "-", "_", ":", etc.
        return re.sub(
            r"[^a-z0-9]+",
            "",
            value
        )

    def build_flexible_header_lookup(schema_result):
        """
        Build:

            exact/flexible human header -> COL$X

        Example:

            Invoice No. -> COL$B
            Discount    -> COL$H
        """

        data = schema_result

        # --------------------------------------------------------
        # Extract MCP text block
        # --------------------------------------------------------

        if isinstance(data, list):
            for block in data:
                if not isinstance(block, dict):
                    continue

                text = block.get("text")

                if not text:
                    continue

                try:
                    data = json.loads(text)
                    break
                except Exception:
                    continue

        if not isinstance(data, dict):
            return {}

        schema = data.get("schema")

        if not isinstance(schema, dict):
            return {}

        properties = schema.get("properties")

        if not isinstance(properties, dict):
            return {}

        lookup = {}

        for property_name, property_info in properties.items():

            if not isinstance(property_info, dict):
                continue

            description = (
                property_info.get("description")
                or ""
            ).strip()

            if not description:
                continue

            normalized = normalize_column_name(
                description
            )

            if normalized:
                lookup[normalized] = {
                    "property": property_name,
                    "header": description
                }

            # Also allow the raw Zapier property itself.
            property_normalized = normalize_column_name(
                property_name
            )

            if property_normalized:
                lookup[property_normalized] = {
                    "property": property_name,
                    "header": description
                }

        return lookup

    # ============================================================
    # STEP 1
    # Resolve spreadsheet
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS RESOLVE: "
            f"finding spreadsheet by name='{spreadsheet_name}'"
        )

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name=(
                    "google_sheets_update_spreadsheet_row"
                ),
                enum_property_name="spreadsheet"
            )
        )

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f"Google Sheet '{spreadsheet_name}' "
                "could not be found."
            )
        }

    print(
        "GOOGLE SHEETS RESOLVE: "
        f"found ID={spreadsheet_id}"
    )

    # ============================================================
    # STEP 2
    # Resolve worksheet
    # ============================================================

    worksheet_result = await _resolve_google_worksheet(
        user_id=user_id,
        mcp_url=mcp_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet
    )

    if worksheet_result.get("status") == "NOT_FOUND":

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet,
            "message": (
                f"Worksheet '{worksheet}' "
                "could not be found."
            )
        }

    if worksheet_result.get("status") == "MULTIPLE":

        return {
            "status": "MULTIPLE_WORKSHEETS",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheets": worksheet_result.get(
                "worksheets",
                []
            ),
            "message": (
                f'The Google Sheet "{spreadsheet_name}" '
                "has multiple worksheets. "
                "Please specify the worksheet."
            )
        }

    if worksheet_result.get("status") == "ERROR":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": worksheet_result.get(
                "message",
                "Unable to determine worksheet."
            ),
            "error": worksheet_result.get("error")
        }

    worksheet = (
        worksheet_result.get("worksheet")
        or worksheet
    )

    print(
        "GOOGLE SHEETS RESOLVED WORKSHEET:",
        worksheet
    )

    # ============================================================
    # STEP 3
    # Resolve schema ONCE
    # ============================================================
    #
    # The old implementation obtains the schema while finding
    # the row and then obtains it AGAIN before performing the
    # update.
    #
    # We resolve it once and reuse it for:
    #
    # - find column
    # - condition column
    # - update columns
    #
    # ============================================================

    try:

        schema_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="get_dynamic_properties_schema",
            params={
                "tool_name": (
                    "google_sheets_update_spreadsheet_row"
                ),
                "tool_arguments": {
                    "spreadsheet": spreadsheet_id,
                    "worksheet": worksheet,
                    "row": (
                        str(row_number)
                        if row_number is not None
                        else "2"
                    ),
                    "dynamic_properties": {}
                }
            }
        )

    except Exception as e:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Unable to determine spreadsheet columns."
            ),
            "error": str(e)
        }

    schema_error = extract_zapier_error(
        schema_result
    )

    if schema_error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Unable to determine spreadsheet columns."
            ),
            "error": schema_error
        }

    header_lookup = (
        build_flexible_header_lookup(
            schema_result
        )
    )

    print(
        "GOOGLE SHEETS FLEXIBLE HEADER LOOKUP:",
        header_lookup
    )

    # ============================================================
    # Helper: resolve a human column name
    # ============================================================

    def resolve_column(column_name):

        normalized = normalize_column_name(
            column_name
        )

        if not normalized:
            return None

        result = header_lookup.get(
            normalized
        )

        if result:
            return result

        return None

    # ============================================================
    # Normalize updates
    # ============================================================
    #
    # Example:
    #
    # AI:
    #
    # {
    #     "discount": 3000
    # }
    #
    # becomes:
    #
    # {
    #     "Discount": 3000
    # }
    #
    # build_google_sheet_dynamic_properties()
    # then converts "Discount" -> COL$H.
    #
    # ============================================================

    canonical_updates = {}

    unknown_update_columns = []

    for column_name, value in updates.items():

        resolved = resolve_column(
            column_name
        )

        if not resolved:

            unknown_update_columns.append(
                column_name
            )

            continue

        canonical_updates[
            resolved["header"]
        ] = value

    if unknown_update_columns:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "One or more update columns "
                "could not be found."
            ),
            "unknown_columns": (
                unknown_update_columns
            ),
            "available_columns": sorted(
                set(
                    item["header"]
                    for item in header_lookup.values()
                    if item.get("header")
                )
            )
        }

    print(
        "GOOGLE SHEETS CANONICAL UPDATES:",
        canonical_updates
    )

    # ============================================================
    # STEP 4
    # Determine target row
    # ============================================================

    target_row_data = None

    # ------------------------------------------------------------
    # CASE A
    # Explicit row number
    # ------------------------------------------------------------

    if row_number is not None:

        try:
            row_number = int(row_number)

        except (TypeError, ValueError):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "row_number must be a valid integer."
                )
            }

        if row_number < 2:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "Row 1 is treated as the header row. "
                    "Please provide a data row number "
                    "starting from row 2."
                )
            }

    # ------------------------------------------------------------
    # CASE B
    # Find row
    # ------------------------------------------------------------

    else:

        find_column = (
            find.get("column") or ""
        ).strip()

        find_value = find.get("value")

        if not find_column:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "Please provide either row_number "
                    "or find.column."
                )
            }

        if find_value is None:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "find.value is required."
                )
            }

        # --------------------------------------------------------
        # Resolve human column name
        # --------------------------------------------------------

        find_property_info = resolve_column(
            find_column
        )

        if not find_property_info:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "message": (
                    f"Column '{find_column}' "
                    "could not be found in "
                    "the spreadsheet."
                ),
                "available_columns": sorted(
                    set(
                        item["header"]
                        for item in header_lookup.values()
                        if item.get("header")
                    )
                )
            }

        find_property = (
            find_property_info["property"]
        )

        canonical_find_column = (
            find_property_info["header"]
        )

        print(
            "GOOGLE SHEETS FIND COLUMN:",
            find_column,
            "->",
            canonical_find_column,
            "->",
            find_property
        )

        # --------------------------------------------------------
        # Read spreadsheet
        # --------------------------------------------------------

        read_result = await _read_google_spreadsheet(
            user_id=user_id,
            mcp_url=mcp_url,
            params={
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "first_row": params.get(
                    "first_row",
                    2
                ),
                "row_count": params.get(
                    "row_count"
                ),
                "batch_size": params.get(
                    "batch_size",
                    1500
                )
            }
        )

        if not isinstance(
            read_result,
            dict
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "Unable to read the spreadsheet "
                    "while locating the target row."
                )
            }

        if read_result.get("status") != "SUCCESS":

            return read_result

        rows = (
            read_result.get("data")
            or []
        )

        first_data_row = params.get(
            "first_row",
            2
        )

        matching_rows = []

        for index, row in enumerate(rows):

            if not isinstance(row, dict):
                continue

            actual_value = row.get(
                find_property
            )

            if not _google_sheet_values_equal(
                actual_value,
                find_value
            ):
                continue

            actual_row_number = (
                first_data_row + index
            )

            matching_rows.append(
                {
                    "row_number": actual_row_number,
                    "data": row
                }
            )

        # --------------------------------------------------------
        # No match
        # --------------------------------------------------------

        if not matching_rows:

            return {
                "status": "NOT_FOUND",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "find": {
                    "column": canonical_find_column,
                    "value": find_value
                },
                "message": (
                    f"No row found where "
                    f"'{canonical_find_column}' "
                    f"equals '{find_value}'."
                )
            }

        # --------------------------------------------------------
        # Multiple matches
        # --------------------------------------------------------

        if len(matching_rows) > 1:

            return {
                "status": "MULTIPLE_ROWS",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "matches": [
                    {
                        "row_number": item[
                            "row_number"
                        ]
                    }
                    for item in matching_rows
                ],
                "message": (
                    f"Multiple rows match "
                    f"'{canonical_find_column}' "
                    f"= '{find_value}'. "
                    "No row was updated. "
                    "Please provide a more specific "
                    "condition or row number."
                )
            }

        # --------------------------------------------------------
        # Exactly one match
        # --------------------------------------------------------

        row_number = matching_rows[0][
            "row_number"
        ]

        target_row_data = matching_rows[0][
            "data"
        ]

        print(
            "GOOGLE SHEETS TARGET ROW:",
            row_number
        )

    # ============================================================
    # STEP 5
    # Optional old-value safety condition
    # ============================================================

    if condition:

        condition_column = (
            condition.get("column") or ""
        ).strip()

        if not condition_column:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "condition.column is required "
                    "when using a condition."
                )
            }

        if "value" not in condition:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "condition.value is required "
                    "when using a condition."
                )
            }

        expected_old_value = condition.get(
            "value"
        )

        condition_property_info = resolve_column(
            condition_column
        )

        if not condition_property_info:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    f"Condition column "
                    f"'{condition_column}' "
                    "could not be found."
                )
            }

        condition_property = (
            condition_property_info["property"]
        )

        canonical_condition_column = (
            condition_property_info["header"]
        )

        print(
            "GOOGLE SHEETS CONDITION COLUMN:",
            condition_column,
            "->",
            canonical_condition_column,
            "->",
            condition_property
        )

        # --------------------------------------------------------
        # If row data isn't available, read the row
        # --------------------------------------------------------

        if target_row_data is None:

            read_result = await _read_google_spreadsheet(
                user_id=user_id,
                mcp_url=mcp_url,
                params={
                    "spreadsheet_id": spreadsheet_id,
                    "spreadsheet_name": spreadsheet_name,
                    "worksheet": worksheet,
                    "first_row": row_number,
                    "row_count": 1,
                    "batch_size": 1
                }
            )

            if not isinstance(
                read_result,
                dict
            ):

                return {
                    "status": "ERROR",
                    "app": "google_sheets",
                    "action": "update_row",
                    "message": (
                        "Unable to verify the "
                        "existing row value."
                    )
                }

            if read_result.get(
                "status"
            ) != "SUCCESS":

                return read_result

            rows = (
                read_result.get("data")
                or []
            )

            if not rows:

                return {
                    "status": "NOT_FOUND",
                    "app": "google_sheets",
                    "action": "update_row",
                    "row_number": row_number,
                    "message": (
                        f"Row {row_number} "
                        "could not be found."
                    )
                }

            target_row_data = rows[0]

        # --------------------------------------------------------
        # Verify old value
        # --------------------------------------------------------

        actual_old_value = target_row_data.get(
            condition_property
        )

        if not _google_sheet_values_equal(
            actual_old_value,
            expected_old_value
        ):

            return {
                "status": "CONDITION_FAILED",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "row_number": row_number,
                "condition": {
                    "column": canonical_condition_column,
                    "value": expected_old_value
                },
                "actual_value": actual_old_value,
                "message": (
                    f"Row {row_number} was not updated "
                    f"because "
                    f"'{canonical_condition_column}' "
                    f"is currently "
                    f"'{actual_old_value}', "
                    f"not '{expected_old_value}'."
                )
            }

    # ============================================================
    # STEP 6
    # Convert human column names -> Zapier dynamic properties
    # ============================================================

    dynamic_properties, dynamic_property_error = (
        build_google_sheet_dynamic_properties(
            schema_result,
            canonical_updates
        )
    )

    if dynamic_property_error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": dynamic_property_error.get(
                "message",
                "Unable to map spreadsheet columns."
            ),
            "error": dynamic_property_error
        }

    print(
        "GOOGLE SHEETS DYNAMIC PROPERTIES:",
        dynamic_properties
    )

    # ============================================================
    # STEP 7
    # Execute Zapier update
    # ============================================================

    print("=" * 60)
    print("GOOGLE SHEETS FINAL UPDATE")
    print("SPREADSHEET ID :", spreadsheet_id)
    print("WORKSHEET      :", worksheet)
    print("ROW            :", row_number)
    print("DYNAMIC PROPS  :", dynamic_properties)
    print("=" * 60)

    try:

        update_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=(
                "google_sheets_update_spreadsheet_row"
            ),
            params={
                "spreadsheet": spreadsheet_id,
                "worksheet": worksheet,
                "row": str(row_number),
                "dynamic_properties": dynamic_properties,

                "output_hint": (
                    "Perform the requested Google Sheets "
                    "row update. Return the actual result "
                    "of the update."
                )
            }
        )

    except Exception as e:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "Unable to update the Google Sheet row."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS UPDATE RAW RESULT ==="
    )
    print(update_result)
    print(
        "=== END GOOGLE SHEETS UPDATE RAW RESULT ==="
    )

    # ============================================================
    # STEP 8
    # Check Zapier error
    # ============================================================

    error = extract_zapier_error(
        update_result
    )

    if error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "The Google Sheet row could not "
                "be updated."
            ),
            "error": error
        }

    # ============================================================
    # STEP 9
    # VERIFY THE UPDATE
    # ============================================================
    #
    # IMPORTANT:
    #
    # Do NOT assume that a successful MCP response means
    # that Google Sheets actually contains the new value.
    #
    # Read the row again and compare the updated columns.
    # ============================================================

    print("=" * 60)
    print("GOOGLE SHEETS UPDATE VERIFICATION")
    print("ROW :", row_number)
    print("=" * 60)

    try:

        verification_result = await _read_google_spreadsheet(
            user_id=user_id,
            mcp_url=mcp_url,
            params={
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "first_row": row_number,
                "row_count": 1,
                "batch_size": 1
            }
        )

    except Exception as e:

        return {
            "status": "UPDATE_UNVERIFIED",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "The Google Sheets update request was sent, "
                "but the updated row could not be verified."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS VERIFICATION RAW RESULT ==="
    )
    print(verification_result)
    print(
        "=== END GOOGLE SHEETS VERIFICATION RAW RESULT ==="
    )

    # ------------------------------------------------------------
    # Verification read failed
    # ------------------------------------------------------------

    if not isinstance(
        verification_result,
        dict
    ):

        return {
            "status": "UPDATE_UNVERIFIED",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "The update request was sent, "
                "but Google Sheets could not be read "
                "to verify the change."
            )
        }

    if verification_result.get(
        "status"
    ) != "SUCCESS":

        return {
            "status": "UPDATE_UNVERIFIED",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "The update request was sent, "
                "but the updated row could not be verified."
            ),
            "verification": verification_result
        }

    verification_rows = (
        verification_result.get("data")
        or []
    )

    if not verification_rows:

        return {
            "status": "UPDATE_UNVERIFIED",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                f"Row {row_number} could not be read "
                "after the update."
            )
        }

    verified_row = verification_rows[0]

    print(
        "GOOGLE SHEETS VERIFIED ROW:",
        verified_row
    )

    # ------------------------------------------------------------
    # Compare every requested update
    # ------------------------------------------------------------

    verification_failures = []

    for column_name, expected_value in canonical_updates.items():

        resolved_column = resolve_column(
            column_name
        )

        if not resolved_column:
            continue

        property_name = resolved_column["property"]

        actual_value = verified_row.get(
            property_name
        )

        print(
            "GOOGLE SHEETS VERIFY COLUMN:",
            column_name,
            "->",
            property_name,
            "| EXPECTED:",
            expected_value,
            "| ACTUAL:",
            actual_value
        )

        if not _google_sheet_values_equal(
            actual_value,
            expected_value
        ):

            verification_failures.append(
                {
                    "column": column_name,
                    "property": property_name,
                    "expected": expected_value,
                    "actual": actual_value
                }
            )

    # ------------------------------------------------------------
    # Verification failed
    # ------------------------------------------------------------

    if verification_failures:

        print(
            "GOOGLE SHEETS UPDATE VERIFICATION FAILED:",
            verification_failures
        )

        return {
            "status": "UPDATE_FAILED",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "updated": canonical_updates,
            "verification_failures": (
                verification_failures
            ),
            "message": (
                f"The update request for row {row_number} "
                "was sent, but Google Sheets still "
                "contains the old value."
            )
        }

    # ============================================================
    # SUCCESS
    # ============================================================

    print("=" * 60)
    print("GOOGLE SHEETS UPDATE VERIFIED SUCCESSFULLY")
    print("ROW :", row_number)
    print("UPDATED :", canonical_updates)
    print("=" * 60)

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "update_row",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet,
        "row_number": row_number,
        "updated": canonical_updates,
        "verified": True,
        "message": (
            f"Row {row_number} was successfully "
            f"updated and verified in "
            f"'{spreadsheet_name}'."
        )
    }

async def _update_google_sheet_row(user_id, mcp_url, params):
    """
    Update an existing Google Sheets row.

    Supports:

    1. Explicit row number

        {
            "row_number": 7,
            "updates": {
                "Salary": 50000
            }
        }

    2. Find row by column/value

        {
            "find": {
                "column": "Invoice No",
                "value": "INV-1001"
            },
            "updates": {
                "Discount": 3000
            }
        }

    3. Find row + optional safety condition

        {
            "find": {
                "column": "Name",
                "value": "Rahul"
            },
            "condition": {
                "column": "Salary",
                "value": 45000
            },
            "updates": {
                "Salary": 50000
            }
        }

    IMPORTANT:

    - Human column names are accepted.
    - Column matching is case-insensitive.
    - Spaces / punctuation / underscores / hyphens are ignored.
    - Actual Google Sheets columns such as COL_B / COL_H are
      discovered from the sheet data.
    - The final Zapier update receives the actual dynamic
      property name, e.g. COL_H.
    - Exactly one matching row is required.
    - The function itself performs exactly one update operation.
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    spreadsheet_id = (
        params.get("spreadsheet_id") or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name") or ""
    ).strip()

    worksheet = (
        params.get("worksheet") or ""
    ).strip()

    row_number = params.get("row_number")

    find = params.get("find") or {}
    condition = params.get("condition") or {}
    updates = params.get("updates") or {}

    print("=" * 70)
    print("GOOGLE SHEETS UPDATE ROW")
    print("SPREADSHEET :", spreadsheet_name)
    print("WORKSHEET   :", worksheet)
    print("ROW         :", row_number)
    print("FIND        :", find)
    print("CONDITION   :", condition)
    print("UPDATES     :", updates)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not spreadsheet_id and not spreadsheet_name:
        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    if not isinstance(updates, dict) or not updates:
        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": (
                "Please provide at least one value "
                "to update."
            )
        }

    # ============================================================
    # NORMALIZATION
    # ============================================================

    def normalize_column_name(value):
        """
        Normalize human column names.

        Examples:

            Invoice no
            Invoice No.
            invoice no.
            INVOICE-NO
            invoice_no

        all become:

            invoiceno
        """

        if value is None:
            return ""

        value = str(value).strip().casefold()

        return re.sub(
            r"[^a-z0-9]+",
            "",
            value
        )

    def normalize_cell_value(value):
        """
        Normalize values for comparison.

        Handles:

            INV-1001
            inv-1001
            " INV-1001 "

        and numeric/currency-like values.
        """

        if value is None:
            return ""

        value = str(value).strip()

        # Remove surrounding whitespace.
        value = value.strip()

        return value.casefold()

    def values_equal(actual, expected):
        """
        Flexible comparison for Google Sheets values.

        Handles:

            "INV-1001" == "INV-1001"
            "INV-1001" == " inv-1001 "

        Also handles numeric values such as:

            3000 == "3000"
            "₹3,000" == 3000
        """

        if actual is None and expected is None:
            return True

        if actual is None or expected is None:
            return False

        actual_text = normalize_cell_value(actual)
        expected_text = normalize_cell_value(expected)

        if actual_text == expected_text:
            return True

        # --------------------------------------------------------
        # Numeric comparison
        # --------------------------------------------------------

        def numeric_value(value):
            try:
                text = str(value).strip()

                # Remove common currency symbols and separators.
                text = re.sub(
                    r"[₹$€£,\s]",
                    "",
                    text
                )

                if not text:
                    return None

                return float(text)

            except Exception:
                return None

        actual_number = numeric_value(actual)
        expected_number = numeric_value(expected)

        if (
            actual_number is not None
            and expected_number is not None
        ):
            return actual_number == expected_number

        return False

    # ============================================================
    # STEP 1
    # RESOLVE SPREADSHEET
    # ============================================================

    if not spreadsheet_id:

        print(
            "GOOGLE SHEETS RESOLVE: "
            f"finding spreadsheet by name='{spreadsheet_name}'"
        )

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name=(
                    "google_sheets_update_spreadsheet_row"
                ),
                enum_property_name="spreadsheet"
            )
        )

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f"Google Sheet '{spreadsheet_name}' "
                "could not be found."
            )
        }

    print(
        "GOOGLE SHEETS RESOLVE: "
        f"found ID={spreadsheet_id}"
    )

    # ============================================================
    # STEP 2
    # RESOLVE WORKSHEET
    # ============================================================

    worksheet_result = await _resolve_google_worksheet(
        user_id=user_id,
        mcp_url=mcp_url,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet
    )

    if worksheet_result.get("status") == "NOT_FOUND":

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet,
            "message": (
                f"Worksheet '{worksheet}' "
                "could not be found."
            )
        }

    if worksheet_result.get("status") == "MULTIPLE":

        return {
            "status": "MULTIPLE_WORKSHEETS",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheets": worksheet_result.get(
                "worksheets",
                []
            ),
            "message": (
                f'The Google Sheet "{spreadsheet_name}" '
                "has multiple worksheets. "
                "Please specify the worksheet."
            )
        }

    if worksheet_result.get("status") == "ERROR":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": worksheet_result.get(
                "message",
                "Unable to determine worksheet."
            ),
            "error": worksheet_result.get("error")
        }

    worksheet = (
        worksheet_result.get("worksheet")
        or worksheet
    )

    print(
        "GOOGLE SHEETS RESOLVED WORKSHEET:",
        worksheet
    )

    # ============================================================
    # STEP 3
    # READ SHEET
    #
    # IMPORTANT:
    #
    # We intentionally use the actual row numbers and COL_X
    # values returned by _read_google_spreadsheet().
    #
    # We do NOT depend on Gemini or the dynamic schema to find
    # the target row.
    # ============================================================

    read_result = await _read_google_spreadsheet(
        user_id=user_id,
        mcp_url=mcp_url,
        params={
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_name": spreadsheet_name,
            "worksheet": worksheet,
            "first_row": params.get(
                "first_row",
                2
            ),
            "row_count": params.get(
                "row_count"
            ),
            "batch_size": params.get(
                "batch_size",
                1500
            )
        }
    )

    if not isinstance(read_result, dict):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Unable to read the spreadsheet "
                "while locating the target row."
            )
        }

    if read_result.get("status") != "SUCCESS":

        return read_result

    rows = read_result.get("data") or []

    if not rows:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "The spreadsheet contains no data rows."
            )
        }

    print(
        "GOOGLE SHEETS UPDATE: "
        f"READ {len(rows)} DATA ROWS"
    )

    # ============================================================
    # STEP 4
    # BUILD COLUMN MAP FROM ACTUAL SHEET DATA
    #
    # The read result looks like:
    #
    # {
    #     "row": 2,
    #     "COL_A": "01-Aug-2026",
    #     "COL_B": "INV-1001",
    #     "COL_C": "ABC Traders",
    #     ...
    #     "COL_H": "₹2,000"
    # }
    #
    # But it does NOT contain human headers.
    #
    # Therefore we need the schema ONLY to identify what
    # COL_B / COL_H represent.
    #
    # If the schema is unavailable, we fall back to a direct
    # header-row read.
    # ============================================================

    column_map = {}

    try:

        schema_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="get_dynamic_properties_schema",
            params={
                "tool_name": (
                    "google_sheets_update_spreadsheet_row"
                ),
                "tool_arguments": {
                    "spreadsheet": spreadsheet_id,
                    "worksheet": worksheet,
                    "row": (
                        str(row_number)
                        if row_number is not None
                        else "2"
                    ),
                    "dynamic_properties": {}
                }
            }
        )

        print(
            "=== GOOGLE SHEETS SCHEMA RESULT ==="
        )
        print(schema_result)
        print(
            "=== END GOOGLE SHEETS SCHEMA RESULT ==="
        )

        # --------------------------------------------------------
        # Extract schema JSON
        # --------------------------------------------------------

        schema_data = schema_result

        if isinstance(schema_data, list):

            for block in schema_data:

                if not isinstance(block, dict):
                    continue

                text = block.get("text")

                if not text:
                    continue

                try:
                    parsed = json.loads(text)

                    if isinstance(parsed, dict):
                        schema_data = parsed
                        break

                except Exception:
                    continue

        if isinstance(schema_data, dict):

            schema = schema_data.get(
                "schema"
            )

            if isinstance(schema, dict):

                properties = schema.get(
                    "properties"
                )

                if isinstance(properties, dict):

                    for property_name, property_info in properties.items():

                        if not isinstance(
                            property_info,
                            dict
                        ):
                            continue

                        description = (
                            property_info.get(
                                "description"
                            )
                            or ""
                        ).strip()

                        if not description:
                            continue

                        normalized_header = (
                            normalize_column_name(
                                description
                            )
                        )

                        normalized_property = (
                            normalize_column_name(
                                property_name
                            )
                        )

                        # Property should normally be COL$A,
                        # COL$B, etc.
                        #
                        # Normalize COL$H -> colh.
                        actual_property = (
                            property_name
                        )

                        entry = {
                            "property": actual_property,
                            "header": description
                        }

                        if normalized_header:
                            column_map[
                                normalized_header
                            ] = entry

                        if normalized_property:
                            column_map[
                                normalized_property
                            ] = entry

    except Exception as e:

        print(
            "GOOGLE SHEETS SCHEMA WARNING:",
            str(e)
        )

    print(
        "GOOGLE SHEETS COLUMN MAP:",
        column_map
    )

    # ============================================================
    # STEP 5
    # BUILD ACTUAL PROPERTY MAP
    #
    # We also support the situation where the schema property
    # is returned as:
    #
    #     COL$B
    #
    # while row data uses:
    #
    #     COL_B
    #
    # Both are converted to the actual row-data key.
    # ============================================================

    def normalize_row_property_name(value):
        """
        Normalize a Zapier property name for matching against
        the properties returned by _read_google_spreadsheet().

        Examples:

            COL$A -> COL_A
            COL$B -> COL_B
            COL$C -> COL_C

        IMPORTANT:
        This function is ONLY for comparing internal row-data keys.

        It must NOT be used for the final Zapier dynamic_properties
        payload because Zapier's dynamic property may require the
        original COL$X form.
        """

        if value is None:
            return ""

        text = str(value).strip().upper()

        return text.replace("$", "_")

    # Convert schema entries to actual row keys.
    normalized_column_map = {}

    for key, info in column_map.items():

        if not isinstance(info, dict):
            continue

        property_name = info.get(
            "property"
        )

        header = info.get(
            "header"
        )

        if not property_name:
            continue

        # Keep the ORIGINAL Zapier property.
        #
        # Example:
        #
        #     COL$C
        #
        # Do NOT convert this to COL_C here.
        #
        # We need the original value for the final
        # dynamic_properties payload.

        zapier_property = str(
            property_name
        ).strip()

        if not zapier_property:
            continue

        normalized_column_map[
            key
        ] = {
            "property": zapier_property,
            "header": header
        }

    column_map = normalized_column_map

    print(
        "GOOGLE SHEETS NORMALIZED COLUMN MAP:",
        column_map
    )

    # ============================================================
    # STEP 6
    # RESOLVE HUMAN COLUMN -> ACTUAL COL_X
    # ============================================================

    def resolve_column(column_name):

        normalized = normalize_column_name(
            column_name
        )

        if not normalized:
            return None

        # --------------------------------------------------------
        # 1. Schema-based human header match
        # --------------------------------------------------------

        result = column_map.get(
            normalized
        )

        if result:
            return result

        # --------------------------------------------------------
        # 2. Direct COL_X support
        #
        # Example:
        #
        # COL_B
        # COL$B
        # --------------------------------------------------------

        direct = str(
            column_name or ""
        ).strip().upper().replace(
            "$",
            "_"
        )

        if re.fullmatch(
            r"COL_[A-Z]+",
            direct
        ):
            return {
                "property": direct,
                "header": direct
            }

        return None

    # ============================================================
    # STEP 7
    # RESOLVE UPDATE COLUMNS
    # ============================================================

    dynamic_properties = {}

    canonical_updates = {}

    unknown_update_columns = []

    for column_name, value in updates.items():

        resolved = resolve_column(
            column_name
        )

        if not resolved:

            unknown_update_columns.append(
                column_name
            )

            continue

        # --------------------------------------------------------
        # IMPORTANT
        #
        # Keep the ORIGINAL Zapier dynamic property exactly as
        # returned by the schema.
        #
        # Example:
        #
        #     COL$C
        #
        # Do NOT convert it to:
        #
        #     COL_C
        #
        # The COL_C form is only used internally by the sheet
        # reader.
        # --------------------------------------------------------

        actual_property = str(
            resolved.get("property") or ""
        ).strip()

        if not actual_property:

            unknown_update_columns.append(
                column_name
            )

            continue

        dynamic_properties[
            actual_property
        ] = value

        canonical_updates[
            resolved.get("header")
            or column_name
        ] = value

        print(
            "GOOGLE SHEETS UPDATE COLUMN:",
            column_name,
            "->",
            resolved.get("header"),
            "->",
            actual_property,
            "=",
            value
        )

    if unknown_update_columns:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "One or more update columns "
                "could not be resolved."
            ),
            "unknown_columns": (
                unknown_update_columns
            ),
            "available_columns": sorted(
                set(
                    item.get("header")
                    for item in column_map.values()
                    if item.get("header")
                )
            )
        }

    if not dynamic_properties:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "No valid spreadsheet columns "
                "were resolved for the update."
            )
        }

    print(
        "GOOGLE SHEETS FINAL DYNAMIC PROPERTIES:",
        dynamic_properties
    )

    # ============================================================
    # STEP 8
    # DETERMINE TARGET ROW
    # ============================================================

    target_row_data = None

    # ------------------------------------------------------------
    # CASE A: explicit row number
    # ------------------------------------------------------------

    if row_number is not None:

        try:

            row_number = int(
                row_number
            )

        except (
            TypeError,
            ValueError
        ):

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "row_number must be a valid integer."
                )
            }

        if row_number < 2:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "Row 1 is the header row. "
                    "Please provide a data row "
                    "starting from row 2."
                )
            }

        # Try to locate the corresponding row from
        # the data we already read.
        for row in rows:

            if not isinstance(row, dict):
                continue

            actual_row = row.get(
                "row"
            )

            try:
                if int(actual_row) == row_number:
                    target_row_data = row
                    break
            except Exception:
                pass

    # ------------------------------------------------------------
    # CASE B: find by column/value
    # ------------------------------------------------------------

    else:

        find_column = (
            find.get("column") or ""
        ).strip()

        if not find_column:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "Please provide either "
                    "row_number or find.column."
                )
            }

        if "value" not in find:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "find.value is required."
                )
            }

        find_value = find.get(
            "value"
        )

        find_info = resolve_column(
            find_column
        )

        if not find_info:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "message": (
                    f"Column '{find_column}' "
                    "could not be resolved."
                ),
                "available_columns": sorted(
                    set(
                        item.get("header")
                        for item in column_map.values()
                        if item.get("header")
                    )
                )
            }

        find_property = normalize_row_property_name(
            find_info.get(
                "property"
            )
        )

        canonical_find_column = (
            find_info.get(
                "header"
            )
            or find_column
        )

        print(
            "GOOGLE SHEETS FIND COLUMN:",
            find_column,
            "->",
            canonical_find_column,
            "->",
            find_property
        )

        # --------------------------------------------------------
        # Find exact row using ACTUAL row number returned by
        # Google Sheets.
        # --------------------------------------------------------

        matching_rows = []

        for row in rows:

            if not isinstance(row, dict):
                continue

            actual_value = row.get(
                find_property
            )

            print(
                "GOOGLE SHEETS COMPARE:",
                find_property,
                "actual=",
                repr(actual_value),
                "expected=",
                repr(find_value)
            )

            if not values_equal(
                actual_value,
                find_value
            ):
                continue

            actual_row_number = row.get(
                "row"
            )

            if actual_row_number is None:
                continue

            try:
                actual_row_number = int(
                    actual_row_number
                )
            except (
                TypeError,
                ValueError
            ):
                continue

            matching_rows.append(
                {
                    "row_number": actual_row_number,
                    "data": row
                }
            )

        print(
            "GOOGLE SHEETS MATCHING ROWS:",
            matching_rows
        )

        # --------------------------------------------------------
        # No match
        # --------------------------------------------------------

        if not matching_rows:

            return {
                "status": "NOT_FOUND",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "find": {
                    "column": canonical_find_column,
                    "value": find_value
                },
                "message": (
                    f"No row found where "
                    f"'{canonical_find_column}' "
                    f"equals '{find_value}'."
                )
            }

        # --------------------------------------------------------
        # Multiple matches
        # --------------------------------------------------------

        if len(matching_rows) > 1:

            return {
                "status": "MULTIPLE_ROWS",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "matches": [
                    {
                        "row_number": item[
                            "row_number"
                        ]
                    }
                    for item in matching_rows
                ],
                "message": (
                    f"Multiple rows match "
                    f"'{canonical_find_column}' "
                    f"= '{find_value}'. "
                    "No row was updated."
                )
            }

        # --------------------------------------------------------
        # Exactly one match
        # --------------------------------------------------------

        target_row_data = matching_rows[0][
            "data"
        ]

        row_number = matching_rows[0][
            "row_number"
        ]

        print(
            "GOOGLE SHEETS TARGET ROW:",
            row_number
        )

    # ============================================================
    # EXPLICIT ROW NOT FOUND
    # ============================================================

    if row_number is not None and target_row_data is None:

        # Read the explicit row directly if it wasn't present
        # in the initial data.
        direct_read = await _read_google_spreadsheet(
            user_id=user_id,
            mcp_url=mcp_url,
            params={
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_name": spreadsheet_name,
                "worksheet": worksheet,
                "first_row": row_number,
                "row_count": 1,
                "batch_size": 1
            }
        )

        if (
            isinstance(direct_read, dict)
            and direct_read.get("status") == "SUCCESS"
        ):

            direct_rows = (
                direct_read.get("data")
                or []
            )

            if direct_rows:
                target_row_data = direct_rows[0]

        if target_row_data is None:

            return {
                "status": "NOT_FOUND",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "row_number": row_number,
                "message": (
                    f"Row {row_number} "
                    "could not be found."
                )
            }

    # ============================================================
    # STEP 9
    # OPTIONAL CONDITION
    # ============================================================

    if condition:

        condition_column = (
            condition.get("column") or ""
        ).strip()

        if not condition_column:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "condition.column is required "
                    "when using a condition."
                )
            }

        if "value" not in condition:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    "condition.value is required "
                    "when using a condition."
                )
            }

        condition_info = resolve_column(
            condition_column
        )

        if not condition_info:

            return {
                "status": "ERROR",
                "app": "google_sheets",
                "action": "update_row",
                "message": (
                    f"Condition column "
                    f"'{condition_column}' "
                    "could not be resolved."
                )
            }

        condition_property = normalize_row_property_name(
            condition_info.get(
                "property"
            )
        )

        canonical_condition_column = (
            condition_info.get(
                "header"
            )
            or condition_column
        )

        expected_old_value = condition.get(
            "value"
        )

        actual_old_value = target_row_data.get(
            condition_property
        )

        print(
            "GOOGLE SHEETS CONDITION:",
            condition_property,
            "actual=",
            repr(actual_old_value),
            "expected=",
            repr(expected_old_value)
        )

        if not values_equal(
            actual_old_value,
            expected_old_value
        ):

            return {
                "status": "CONDITION_FAILED",
                "app": "google_sheets",
                "action": "update_row",
                "spreadsheet_name": spreadsheet_name,
                "spreadsheet_id": spreadsheet_id,
                "worksheet": worksheet,
                "row_number": row_number,
                "condition": {
                    "column": canonical_condition_column,
                    "value": expected_old_value
                },
                "actual_value": actual_old_value,
                "message": (
                    f"Row {row_number} was not updated "
                    f"because "
                    f"'{canonical_condition_column}' "
                    f"is currently "
                    f"'{actual_old_value}', "
                    f"not '{expected_old_value}'."
                )
            }

    # ============================================================
    # STEP 10
    # FINAL SAFETY CHECK
    # ============================================================

    if not row_number:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "message": (
                "Unable to determine the target row."
            )
        }

    print("=" * 70)
    print("GOOGLE SHEETS FINAL UPDATE")
    print("SPREADSHEET :", spreadsheet_id)
    print("WORKSHEET   :", worksheet)
    print("ROW         :", row_number)
    print("UPDATES     :", canonical_updates)
    print("DYNAMIC     :", dynamic_properties)
    print("=" * 70)

    # ============================================================
    # STEP 11
    # EXECUTE EXACTLY ONE ZAPIER UPDATE
    # ============================================================

    try:

        update_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=(
                "google_sheets_update_spreadsheet_row"
            ),
            params={
                "spreadsheet": spreadsheet_id,
                "worksheet": worksheet,
                "row": str(row_number),
                "dynamic_properties": dynamic_properties,
                "output_hint": (
                    "Return only a concise confirmation "
                    "of the row update. "
                    "Do not request another tool call."
                )
            }
        )

    except Exception as e:

        print(
            "GOOGLE SHEETS UPDATE EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "Unable to update the Google Sheet row."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE SHEETS UPDATE RAW RESULT ==="
    )
    print(update_result)
    print(
        "=== END GOOGLE SHEETS UPDATE RAW RESULT ==="
    )

    # ============================================================
    # STEP 12
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        update_result
    )

    if error:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "update_row",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "row_number": row_number,
            "message": (
                "The Google Sheet row could not "
                "be updated."
            ),
            "error": error
        }

    # ============================================================
    # SUCCESS
    #
    # Return a very clear deterministic application result.
    #
    # Do NOT include the raw Zapier response.
    # ============================================================

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "update_row",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet,
        "row_number": row_number,
        "updated": canonical_updates,
        "dynamic_properties": dynamic_properties,
        "message": (
            f"Row {row_number} successfully updated "
            f"in '{spreadsheet_name}'."
        )
    }
    
async def _calculate_google_spreadsheet(user_id, mcp_url, params):

    spreadsheet_name = (
        params.get("spreadsheet_name")
        or ""
    ).strip()

    spreadsheet_id = (
        params.get("spreadsheet_id")
        or ""
    ).strip()

    worksheet = (
        params.get("worksheet")
        or ""
    ).strip()

    calculation_request = (
        params.get("calculation_request")
        or params.get("instruction")
        or params.get("query")
        or ""
    ).strip()

    print("=" * 60)
    print("GOOGLE SHEETS CALCULATION")
    print(f"SPREADSHEET : {spreadsheet_name}")
    print(f"SPREADSHEET ID : {spreadsheet_id}")
    print(f"WORKSHEET : {worksheet}")
    print(f"CALCULATION_REQUEST : {calculation_request}")
    print("=" * 60)

    if not spreadsheet_name and not spreadsheet_id:

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "calculate_spreadsheet",
            "message": (
                "Please provide spreadsheet_name "
                "or spreadsheet_id."
            )
        }

    # ------------------------------------------------------------
    # STEP 1
    # Resolve spreadsheet ID
    # ------------------------------------------------------------

    if not spreadsheet_id:

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_name=spreadsheet_name
            )
        )

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "calculate_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f"Google Sheet '{spreadsheet_name}' "
                "could not be found."
            )
        }

    # ------------------------------------------------------------
    # STEP 2
    # Read all rows using existing paging implementation
    # ------------------------------------------------------------

    read_params = {
        "spreadsheet_id": spreadsheet_id,
        "spreadsheet_name": spreadsheet_name,
        "worksheet": worksheet,
        "first_row": params.get("first_row", 2),
        "row_count": params.get("row_count"),
        "batch_size": params.get("batch_size", 1500),
    }

    read_result = await _read_google_spreadsheet(
        user_id=user_id,
        mcp_url=mcp_url,
        params=read_params
    )

    if not isinstance(read_result, dict):

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "calculate_spreadsheet",
            "message": (
                "Unable to read spreadsheet data."
            ),
            "data": read_result
        }

    if read_result.get("status") != "SUCCESS":

        return read_result

    rows = read_result.get("data") or []

    # ------------------------------------------------------------
    # STEP 3
    # Calculate
    # ------------------------------------------------------------

    if not calculation_request:
        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "calculate_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "message": (
                "Please provide the calculation you want "
                "to perform."
            )
        }

    try:

        calculation_result = await calculate_with_ai(rows=rows, calculation_request=calculation_request,)

        result = calculation_result.get("result")
        calculation_plan = calculation_result.get("plan")

    except Exception as e:

        print(
            "GOOGLE SHEETS AI CALCULATION ERROR:",
            e
        )

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "calculate_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "worksheet": worksheet,
            "calculation_request": calculation_request,
            "message": (
                "Unable to perform the requested "
                "calculation."
            ),
            "error": str(e)
        }

    return {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "calculate_spreadsheet",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "worksheet": worksheet,
        "calculation_request": calculation_request,
        "result": result,
        "calculation_plan": calculation_plan,
        "row_count": len(rows),
        "message": (
            "Calculation completed successfully."
        )
    }

async def _share_google_spreadsheet(user_id, mcp_url, params):
    """
    Share a Google Spreadsheet.

    Google Sheets uses Google Drive sharing because a
    spreadsheet is a Google Drive file.

    Accepted aliases:

        spreadsheet_name
        document_name
        file

    for the spreadsheet name.

    Accepted ID aliases:

        spreadsheet_id
        file_id
    """

    # ========================================================
    # INPUTS
    # ========================================================

    spreadsheet_id = (
        params.get("spreadsheet_id")
        or params.get("file_id")
        or ""
    ).strip()

    spreadsheet_name = (
        params.get("spreadsheet_name")
        or params.get("document_name")
        or params.get("file")
        or ""
    ).strip()

    email = normalize_email(
        params.get("email")
        or ""
    )

    permission = (
        params.get("permission")
        or "email"
    ).strip().lower()

    role = (
        params.get("role")
        or ""
    ).strip().lower()

    print("=" * 70)
    print("GOOGLE SHEETS SHARE")
    print("SPREADSHEET NAME :", spreadsheet_name)
    print("SPREADSHEET ID   :", spreadsheet_id)
    print("EMAIL            :", email)
    print("PERMISSION       :", permission)
    print("ROLE             :", role)
    print("=" * 70)

    # ========================================================
    # STEP 1
    # Resolve spreadsheet ID
    # ========================================================

    if not spreadsheet_id:

        spreadsheet_id = (
            await _resolve_google_spreadsheet_id(
                user_id=user_id,
                mcp_url=mcp_url,
                spreadsheet_id=None,
                spreadsheet_name=spreadsheet_name,
                tool_name=(
                    GOOGLE_DRIVE_SHARE_TOOL
                ),
                enum_property_name="file_id"
            )
        )

    if not spreadsheet_id:

        return {
            "status": "NOT_FOUND",
            "app": "google_sheets",
            "action": "share_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "message": (
                f"Google Spreadsheet "
                f"'{spreadsheet_name}' "
                "could not be found."
            )
        }

    # ========================================================
    # STEP 2
    # Build common sharing properties
    # ========================================================

    props_result = (
        await _google_build_share_dynamic_properties(
            user_id=user_id,
            mcp_url=mcp_url,
            file_id=spreadsheet_id,
            permission=permission,
            email=email,
            role=role,
            file_name=spreadsheet_name
        )
    )

    if props_result.get("status") != "SUCCESS":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "share_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "message": props_result.get(
                "message",
                "Unable to prepare sharing request."
            )
        }

    # ========================================================
    # STEP 3
    # Execute common Drive sharing
    # ========================================================

    share_result = (
        await _google_execute_drive_share(
            user_id=user_id,
            mcp_url=mcp_url,
            file_id=spreadsheet_id,
            permission=permission,
            dynamic_properties=(
                props_result[
                    "dynamic_properties"
                ]
            ),
            output_hint=(
                "Return confirmation that the Google "
                "Spreadsheet was shared successfully. "
                "Include spreadsheet ID, permission, "
                "recipient if applicable, and sharing "
                "URL if available."
            )
        )
    )

    if share_result.get("status") != "SUCCESS":

        return {
            "status": "ERROR",
            "app": "google_sheets",
            "action": "share_spreadsheet",
            "spreadsheet_name": spreadsheet_name,
            "spreadsheet_id": spreadsheet_id,
            "permission": permission,
            "message": (
                "Google Spreadsheet sharing failed."
            ),
            "error": share_result.get("error")
        }

    # ========================================================
    # STEP 4
    # Final response
    # ========================================================

    if permission == "email":

        access_text = (
            f'with {email} as '
            f'{_google_normalize_role(role) or "reader"}'
        )

        message = (
            f'Google Spreadsheet '
            f'"{spreadsheet_name or spreadsheet_id}" '
            f'was shared successfully {access_text}. '
            f'A sharing notification email was sent.'
        )

    else:

        message = (
            f'Google Spreadsheet '
            f'"{spreadsheet_name or spreadsheet_id}" '
            f'was shared successfully.'
        )

    response = {
        "status": "SUCCESS",
        "app": "google_sheets",
        "action": "share_spreadsheet",
        "spreadsheet_name": spreadsheet_name,
        "spreadsheet_id": spreadsheet_id,
        "permission": permission,
        "email": email or None,
        "role": _google_normalize_role(role) or None,
        "message": message
    }

    if share_result.get("sharing_url"):

        response["sharing_url"] = (
            share_result["sharing_url"]
        )

    return response

# endregion


# region GOOGLE CALENDAR

# ============================================================
# GOOGLE CALENDAR
# ============================================================

async def _resolve_google_calendar_id(user_id, mcp_url, calendar_id=None):
    """
    Resolve a Google Calendar ID for
    google_calendar_create_detailed_event.

    If calendar_id is supplied, use it directly.

    Otherwise ask Zapier for the available calendar
    dynamic enum values and select the primary/default
    calendar when available.
    """

    manager = get_zapier_manager()

    calendar_id = (
        calendar_id or ""
    ).strip()

    # ============================================================
    # EXPLICIT CALENDAR
    # ============================================================

    if calendar_id:

        print(
            "GOOGLE CALENDAR RESOLVE: "
            f"using supplied calendar='{calendar_id}'"
        )

        return {
            "status": "FOUND",
            "calendarid": calendar_id
        }

    # ============================================================
    # RESOLVE DYNAMIC ENUM
    # ============================================================

    print(
        "GOOGLE CALENDAR RESOLVE: "
        "calendar not supplied; resolving dynamic enum"
    )

    try:

        enum_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="list_dynamic_enum_values",
            params={
                "tool_name": (
                    "google_calendar_create_detailed_event"
                ),
                "property_name": "calendarid",
                "search": ""
            }
        )

    except Exception as e:

        print(
            "GOOGLE CALENDAR RESOLVE ERROR:",
            str(e)
        )

        return {
            "status": "ERROR",
            "calendarid": None,
            "message": (
                "Unable to determine the Google Calendar."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE CALENDAR ENUM RESULT ==="
    )
    print(enum_result)
    print(
        "=== END GOOGLE CALENDAR ENUM RESULT ==="
    )

    # ============================================================
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        enum_result
    )

    if error:

        return {
            "status": "ERROR",
            "calendarid": None,
            "message": (
                "Unable to determine the Google Calendar."
            ),
            "error": error
        }

    # ============================================================
    # PARSE RESULT
    # ============================================================

    data = enum_result

    if isinstance(
        data,
        list
    ):

        for block in data:

            if not isinstance(
                block,
                dict
            ):
                continue

            text = block.get("text")

            if not text:
                continue

            try:

                parsed = json.loads(text)

                if isinstance(
                    parsed,
                    dict
                ):

                    data = parsed
                    break

            except Exception:

                continue

    if not isinstance(
        data,
        dict
    ):

        return {
            "status": "ERROR",
            "calendarid": None,
            "message": (
                "Invalid calendar information "
                "was returned by Zapier."
            )
        }

    values = data.get("values")

    if not isinstance(
        values,
        list
    ):

        return {
            "status": "ERROR",
            "calendarid": None,
            "message": (
                "Zapier did not return a list of calendars."
            )
        }

    # ============================================================
    # EXTRACT CALENDARS
    # ============================================================

    calendars = []

    for item in values:

        if not isinstance(
            item,
            dict
        ):
            continue

        value = str(
            item.get("value") or ""
        ).strip()

        label = str(
            item.get("label") or value
        ).strip()

        if value:

            calendars.append({
                "value": value,
                "label": label
            })

    print(
        "GOOGLE CALENDAR AVAILABLE CALENDARS:",
        calendars
    )

    # ============================================================
    # NO CALENDARS
    # ============================================================

    if not calendars:

        return {
            "status": "NOT_FOUND",
            "calendarid": None,
            "message": (
                "No Google Calendars were found."
            )
        }

    # ============================================================
    # PREFER PRIMARY
    # ============================================================

    for calendar in calendars:

        value = calendar["value"].strip().casefold()
        label = calendar["label"].strip().casefold()

        if (
            value == "primary"
            or label == "primary"
            or "primary" in label
        ):

            print(
                "GOOGLE CALENDAR RESOLVE: "
                f"selected primary calendar='{calendar['value']}'"
            )

            return {
                "status": "FOUND",
                "calendarid": calendar["value"],
                "calendar_name": calendar["label"],
                "calendars": calendars
            }

    # ============================================================
    # FALLBACK
    #
    # Use first available calendar.
    # ============================================================

    selected = calendars[0]

    print(
        "GOOGLE CALENDAR RESOLVE: "
        f"selected first calendar='{selected['value']}'"
    )

    return {
        "status": "FOUND",
        "calendarid": selected["value"],
        "calendar_name": selected["label"],
        "calendars": calendars
    }

async def _create_google_calendar_event(*, user_id, mcp_url, params):
    """
    Create a Google Calendar event.

    Supported input:

    {
        "title": "Team Meeting",
        "start": "2026-08-28T10:00:00+05:30",
        "end": "2026-08-28T11:00:00+05:30"
    }

    Optional:

    {
        "calendarid": "...",
        "description": "...",
        "location": "...",
        "attendees": ["person@example.com"]
    }

    Zapier MCP tool:
        google_calendar_create_detailed_event
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    title = (
        params.get("title")
        or params.get("summary")
        or ""
    ).strip()

    start_time = (
        params.get("start")
        or params.get("start_time")
        or params.get("start__dateTime")
        or ""
    ).strip()

    end_time = (
        params.get("end")
        or params.get("end_time")
        or params.get("end__dateTime")
        or ""
    ).strip()

    calendar_id = (
        params.get("calendarid")
        or params.get("calendar_id")
        or ""
    ).strip()

    description = (
        params.get("description")
        or ""
    ).strip()

    location = (
        params.get("location")
        or ""
    ).strip()

    attendees = params.get("attendees")

    calendar_result = await _resolve_google_calendar_id(
        user_id=user_id,
        mcp_url=mcp_url,
        calendar_id=calendar_id
    )

    print(
        "GOOGLE CALENDAR RESOLVE RESULT:",
        calendar_result
    )

    if calendar_result.get("status") != "FOUND":

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "create_event",
            "title": title,
            "start": start_time,
            "end": end_time,
            "message": (
                calendar_result.get("message")
                or
                "Unable to determine the Google Calendar."
            ),
            "error": calendar_result.get("error")
        }

    calendar_id = calendar_result["calendarid"]

    # ============================================================
    # LOGGING
    # ============================================================

    print("=" * 70)
    print("GOOGLE CALENDAR CREATE EVENT")
    print("TITLE        :", title)
    print("START        :", start_time)
    print("END          :", end_time)
    print("CALENDAR ID  :", calendar_id)
    print("DESCRIPTION  :", description)
    print("LOCATION     :", location)
    print("ATTENDEES    :", attendees)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not title:

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "create_event",
            "message": (
                "Please provide an event title."
            )
        }

    if not start_time:

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "create_event",
            "message": (
                "Please provide the event start date and time."
            )
        }

    if not end_time:

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "create_event",
            "message": (
                "Please provide the event end date and time."
            )
        }

    # ============================================================
    # BUILD ZAPIER PARAMETERS
    # ============================================================

    tool_params = {
        "summary": title,
        "start__dateTime": start_time,
        "end__dateTime": end_time,
        "calendarid": calendar_id,
        "eventType": "default",
        "output_hint": (
            "Return the created Google Calendar event "
            "title, start time, end time, event ID, "
            "and event link if available."
        )
    }

    # ------------------------------------------------------------
    # Optional calendar
    #
    # If omitted, Zapier/Google Calendar can use the
    # connected/default calendar.
    # ------------------------------------------------------------

    if calendar_id:
        tool_params["calendarid"] = calendar_id

    # ------------------------------------------------------------
    # Optional fields
    # ------------------------------------------------------------

    if description:
        tool_params["description"] = description

    if location:
        tool_params["location"] = location

    if attendees:

        if isinstance(attendees, str):

            attendees = [
                email.strip()
                for email in attendees.split(",")
                if email.strip()
            ]

        if isinstance(attendees, list) and attendees:
            tool_params["attendees"] = attendees

    # ============================================================
    # EXECUTE ZAPIER MCP TOOL
    # ============================================================

    print(
        "GOOGLE CALENDAR CREATE EVENT: "
        "calling google_calendar_create_detailed_event"
    )

    print(
        "GOOGLE CALENDAR CREATE EVENT PARAMS:",
        tool_params
    )

    try:

        create_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_calendar_create_detailed_event",
            params=tool_params
        )

    except Exception as e:

        print(
            "GOOGLE CALENDAR CREATE EVENT EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "create_event",
            "title": title,
            "start": start_time,
            "end": end_time,
            "message": (
                "Unable to create the Google Calendar event."
            ),
            "error": str(e)
        }

    # ============================================================
    # RAW RESULT
    # ============================================================

    print(
        "=== GOOGLE CALENDAR CREATE EVENT RAW RESULT ==="
    )

    print(create_result)

    print(
        "=== END GOOGLE CALENDAR CREATE EVENT RAW RESULT ==="
    )

    # ============================================================
    # CHECK ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(
        create_result
    )

    if error:

        print(
            "GOOGLE CALENDAR CREATE EVENT ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "create_event",
            "title": title,
            "start": start_time,
            "end": end_time,
            "message": (
                "The Google Calendar event could not be created."
            ),
            "error": error
        }

    # ============================================================
    # PARSE RESULT
    # ============================================================

    result_data = create_result

    if isinstance(
        result_data,
        list
    ):

        for block in result_data:

            if not isinstance(
                block,
                dict
            ):
                continue

            text = block.get("text")

            if not text:
                continue

            try:

                parsed = json.loads(text)

                if isinstance(
                    parsed,
                    dict
                ):

                    result_data = parsed
                    break

            except Exception:

                continue

    # ============================================================
    # EXPLICIT MCP ERROR
    # ============================================================

    if isinstance(
        result_data,
        dict
    ):

        if result_data.get("isError"):

            return {
                "status": "ERROR",
                "app": "google_calendar",
                "action": "create_event",
                "title": title,
                "start": start_time,
                "end": end_time,
                "message": (
                    "The Google Calendar event could not "
                    "be created."
                ),
                "error": (
                    result_data.get("error")
                    or
                    "Google Calendar event creation failed."
                )
            }

    # ============================================================
    # SUCCESS
    #
    # Don't depend on a specific Zapier response structure.
    # The tool invocation itself succeeded and no Zapier/MCP
    # error was detected.
    # ============================================================

    event_result = None

    if isinstance(
        result_data,
        dict
    ):

        event_result = (
            result_data.get("results")
            or result_data.get("result")
        )

    print(
        "GOOGLE CALENDAR CREATE EVENT: "
        "CREATE OPERATION SUCCESSFUL"
    )

    return {
        "status": "SUCCESS",
        "app": "google_calendar",
        "action": "create_event",
        "title": title,
        "start": start_time,
        "end": end_time,
        "calendarid": calendar_id or None,
        "message": (
            f'Calendar event "{title}" '
            "was created successfully."
        ),
        "result": event_result
    }

async def _list_google_calendar_events(*, user_id, mcp_url, params):
    """
    List/find Google Calendar events.

    Supports:

        {}
            -> upcoming events from now

        {
            "start_time": "...",
            "end_time": "..."
        }

        {
            "search_term": "Team Meeting"
        }

        {
            "attendee_email": "test8cs@gmail.com"
        }

    Optional:
        - calendarid
        - eventTypes
        - ordering
        - search_term
        - attendee_email
        - expand_recurring
        - paging_token

    Important:
        Zapier's google_calendar_find_events schema uses:

            end_time   = lower boundary / earliest timestamp
            start_time = upper boundary / latest timestamp

        Do NOT reverse these when passing them to Zapier.
    """

    manager = get_zapier_manager()

    calendar_id = (
        params.get("calendarid")
        or params.get("calendar_id")
        or ""
    ).strip()

    start_time = (
        params.get("start_time")
        or ""
    ).strip()

    end_time = (
        params.get("end_time")
        or ""
    ).strip()

    search_term = (
        params.get("search_term")
        or ""
    ).strip()

    attendee_email = normalize_email(
        params.get("attendee_email")
        or ""
    )

    ordering = (
        params.get("ordering")
        or ""
    ).strip()

    event_types = params.get("eventTypes")

    expand_recurring = params.get(
        "expand_recurring",
        True
    )

    paging_token = (
        params.get("paging_token")
        or ""
    ).strip()

    print("=" * 70)
    print("GOOGLE CALENDAR LIST EVENTS")
    print("CALENDAR ID       :", calendar_id)
    print("LOWER BOUNDARY    :", end_time)
    print("UPPER BOUNDARY    :", start_time)
    print("SEARCH TERM       :", search_term)
    print("ATTENDEE EMAIL    :", attendee_email)
    print("ORDERING          :", ordering)
    print("EVENT TYPES       :", event_types)
    print("EXPAND RECURRING  :", expand_recurring)
    print("PAGING TOKEN      :", paging_token)
    print("=" * 70)

    # ============================================================
    # DEFAULT CALENDAR
    # ============================================================

    # google_calendar_find_events requires calendarid as a
    # dynamic enum. For the user's normal personal calendar,
    # resolve the valid enum value instead of guessing "primary".
    if not calendar_id:

        print(
            "GOOGLE CALENDAR LIST: "
            "calendarid not supplied; resolving default calendar"
        )

        try:

            enum_result = await manager.execute_tool(
                user_id=user_id,
                mcp_url=mcp_url,
                tool_name="list_dynamic_enum_values",
                params={
                    "tool_name":
                        "google_calendar_find_events",
                    "property_name":
                        "calendarid"
                }
            )

            print(
                "=== GOOGLE CALENDAR CALENDAR ENUM RESULT ==="
            )
            print(enum_result)
            print(
                "=== END GOOGLE CALENDAR CALENDAR ENUM RESULT ==="
            )

            calendar_id = (
                _extract_google_calendar_default_id(
                    enum_result
                )
            )

        except Exception as e:

            print(
                "GOOGLE CALENDAR CALENDAR ENUM ERROR:",
                str(e)
            )

            return {
                "status": "ERROR",
                "app": "google_calendar",
                "action": "list_events",
                "message": (
                    "Unable to determine the default "
                    "Google Calendar."
                ),
                "error": str(e)
            }

    if not calendar_id:

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "list_events",
            "message": (
                "Unable to determine the Google Calendar "
                "to search."
            )
        }

    # ============================================================
    # BUILD ZAPIER PARAMETERS
    # ============================================================

    tool_params = {
        "calendarid": calendar_id,

        "output_hint": (
            "Return the matching Google Calendar events. "
            "For each event include the event title, "
            "start time, end time, event ID, event link, "
            "description, location, and attendees when "
            "available."
        )
    }

    # ------------------------------------------------------------
    # Time boundaries
    # ------------------------------------------------------------

    if end_time:
        tool_params["end_time"] = end_time

    if start_time:
        tool_params["start_time"] = start_time

    # ------------------------------------------------------------
    # Optional filters
    # ------------------------------------------------------------

    if ordering:
        tool_params["ordering"] = ordering

    if search_term:
        tool_params["search_term"] = search_term

    if attendee_email:
        tool_params["attendee_email"] = attendee_email

    if event_types:
        tool_params["eventTypes"] = event_types

    if paging_token:
        tool_params["paging_token"] = paging_token

    # ------------------------------------------------------------
    # Recurring events
    #
    # This property changes dynamic_properties schema.
    # Therefore schema resolution must happen after setting it.
    # ------------------------------------------------------------

    if expand_recurring is not None:
        tool_params["expand_recurring"] = (
            expand_recurring
        )

    # ============================================================
    # DYNAMIC PROPERTY SCHEMA
    # ============================================================

    dynamic_properties = {}

    try:

        schema_result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="get_dynamic_properties_schema",
            params={
                "tool_name":
                    "google_calendar_find_events",

                "tool_arguments":
                    {
                        **tool_params,
                        "dynamic_properties": {}
                    }
            }
        )

        print(
            "=== GOOGLE CALENDAR FIND EVENTS "
            "DYNAMIC SCHEMA ==="
        )
        print(schema_result)
        print(
            "=== END GOOGLE CALENDAR FIND EVENTS "
            "DYNAMIC SCHEMA ==="
        )

        # At the moment we don't invent any dynamic fields.
        #
        # The supplied schema says dynamic_properties depends
        # on expand_recurring, so resolving it is required before
        # executing the operation.
        dynamic_properties = {}

    except Exception as e:

        print(
            "GOOGLE CALENDAR DYNAMIC SCHEMA ERROR:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "list_events",
            "calendar_id": calendar_id,
            "message": (
                "Unable to determine the Google Calendar "
                "search properties."
            ),
            "error": str(e)
        }

    # ============================================================
    # EXECUTE ZAPIER ACTION
    # ============================================================

    tool_params["dynamic_properties"] = (
        dynamic_properties
    )

    print(
        "GOOGLE CALENDAR LIST EVENTS: "
        "calling google_calendar_find_events"
    )

    print(
        "GOOGLE CALENDAR LIST EVENTS PARAMS:",
        tool_params
    )

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_calendar_find_events",
            params=tool_params
        )

    except Exception as e:

        print(
            "GOOGLE CALENDAR LIST EVENTS EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "list_events",
            "calendar_id": calendar_id,
            "message": (
                "Unable to retrieve Google Calendar events."
            ),
            "error": str(e)
        }

    print(
        "=== GOOGLE CALENDAR LIST EVENTS RAW RESULT ==="
    )
    print(result)
    print(
        "=== END GOOGLE CALENDAR LIST EVENTS RAW RESULT ==="
    )

    # ============================================================
    # ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(result)

    if error:

        print(
            "GOOGLE CALENDAR LIST EVENTS ERROR:",
            error
        )

        return {
            "status": "ERROR",
            "app": "google_calendar",
            "action": "list_events",
            "calendar_id": calendar_id,
            "message": (
                "Google Calendar events could not be retrieved."
            ),
            "error": error
        }

    # ============================================================
    # PARSE RESULT
    # ============================================================

    data = _google_parse_mcp_json(result)

    events = _extract_google_calendar_events(
        data
    )

    paging = _extract_google_calendar_paging_token(
        data
    )

    print(
        "GOOGLE CALENDAR LIST EVENTS: "
        f"found {len(events)} events"
    )

    # ============================================================
    # SUCCESS
    # ============================================================

    return {
        "status": "SUCCESS",
        "app": "google_calendar",
        "action": "list_events",
        "calendar_id": calendar_id,
        "events": events,
        "count": len(events),
        "paging_token": paging,
        "data": data
    }

def _extract_google_calendar_default_id(result):
    """
    Extract a usable calendar ID from the dynamic enum
    returned by Zapier.

    Example:

        {
            "values": [
                {
                    "value": "test8cs@gmail.com",
                    "label": "Sanjay Singh"
                }
            ]
        }

    We prefer the first non-Birthdays calendar.
    """

    if not result:
        return None

    data = _google_parse_mcp_json(result)

    # ------------------------------------------------------------
    # Sometimes the MCP result is still a content-block list
    # ------------------------------------------------------------

    if isinstance(data, list):

        for item in data:

            if not isinstance(item, dict):
                continue

            if "values" in item:
                data = item
                break

    if not isinstance(data, dict):
        return None

    values = data.get("values")

    if not isinstance(values, list):
        return None

    candidates = []

    for item in values:

        if not isinstance(item, dict):
            continue

        value = (
            item.get("value")
            or ""
        ).strip()

        label = (
            item.get("label")
            or ""
        ).strip()

        if not value:
            continue

        # Never select Birthdays as the default calendar.
        combined = (
            f"{label} {value}"
        ).lower()

        if "birthdays" in combined:
            continue

        candidates.append(
            {
                "value": value,
                "label": label
            }
        )

    if not candidates:
        return None

    # Prefer "primary" if Zapier happens to expose it.
    for item in candidates:

        if item["value"].lower() == "primary":
            return item["value"]

    # Otherwise use the first valid personal calendar.
    return candidates[0]["value"]

def _extract_google_calendar_events(data):
    """
    Normalize Google Calendar find-events output.

    Returns a list of event dictionaries.
    """

    if not data:
        return []

    candidates = []

    # ------------------------------------------------------------
    # Direct results
    # ------------------------------------------------------------

    if isinstance(data, dict):

        results = data.get("results")

        if isinstance(results, list):
            candidates.extend(results)

        elif isinstance(results, dict):
            candidates.append(results)

        # Some responses may use events directly.
        events = data.get("events")

        if isinstance(events, list):
            candidates.extend(events)

    elif isinstance(data, list):

        for item in data:

            if isinstance(item, dict):

                if isinstance(
                    item.get("results"),
                    list
                ):
                    candidates.extend(
                        item["results"]
                    )

                elif isinstance(
                    item.get("results"),
                    dict
                ):
                    candidates.append(
                        item["results"]
                    )

    normalized = []

    for event in candidates:

        if not isinstance(event, dict):
            continue

        normalized.append(
            {
                "event_id": (
                    event.get("event_id")
                    or event.get("eventId")
                    or event.get("id")
                ),

                "title": (
                    event.get("title")
                    or event.get("summary")
                    or event.get("name")
                ),

                "start_time": (
                    event.get("start_time")
                    or event.get("startTime")
                    or (
                        event.get("start", {})
                        .get("dateTime")
                        if isinstance(
                            event.get("start"),
                            dict
                        )
                        else None
                    )
                ),

                "end_time": (
                    event.get("end_time")
                    or event.get("endTime")
                    or (
                        event.get("end", {})
                        .get("dateTime")
                        if isinstance(
                            event.get("end"),
                            dict
                        )
                        else None
                    )
                ),

                "event_link": (
                    event.get("event_link")
                    or event.get("eventLink")
                    or event.get("htmlLink")
                    or event.get("webLink")
                ),

                "description": (
                    event.get("description")
                ),

                "location": (
                    event.get("location")
                ),

                "attendees": (
                    event.get("attendees")
                )
            }
        )

    return normalized

def _extract_google_calendar_paging_token(data):
    """
    Extract the pagination cursor returned by
    google_calendar_find_events.
    """

    if not data:
        return None

    if isinstance(data, dict):

        for key in (
            "paging_token",
            "next_page_token",
            "nextPageToken"
        ):

            value = data.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        results = data.get("results")

        if isinstance(results, dict):

            for key in (
                "paging_token",
                "next_page_token",
                "nextPageToken"
            ):

                value = results.get(key)

                if (
                    isinstance(value, str)
                    and value.strip()
                ):
                    return value.strip()

    return None

def _google_calendar_extract_result(result):
    """
    Extract parsed JSON from a Zapier/MCP result.

    Supports:
        [
            {
                "type": "text",
                "text": "{...}"
            }
        ]

    and direct dictionaries.
    """

    if isinstance(result, dict):
        return result

    if isinstance(result, list):

        for item in result:

            if not isinstance(item, dict):
                continue

            text = item.get("text")

            if not text:
                continue

            try:
                return json.loads(text)
            except Exception:
                continue

    if isinstance(result, str):

        try:
            return json.loads(result)
        except Exception:
            return None

    return None

def _google_calendar_find_result_data(result):
    """
    Extract the `results` object/list from a Zapier response.
    """

    data = _google_calendar_extract_result(result)

    if not isinstance(data, dict):
        return None

    if "results" in data:
        return data["results"]

    return data

def _google_calendar_first_string(data, keys):
    """
    Recursively find the first non-empty string value
    for one of the supplied keys.
    """

    if isinstance(data, dict):

        for key in keys:

            value = data.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        for value in data.values():

            found = _google_calendar_first_string(
                value,
                keys
            )

            if found:
                return found

    elif isinstance(data, list):

        for item in data:

            found = _google_calendar_first_string(
                item,
                keys
            )

            if found:
                return found

    return None

def _google_calendar_extract_event_id(result):
    """
    Extract event ID from google_calendar_find_events
    or google_calendar_update_event result.
    """

    return _google_calendar_first_string(
        result,
        (
            "event_id",
            "eventId",
            "eventid",
            "id",
        )
    )

def _google_calendar_extract_event_title(result):
    """
    Extract event title.
    """

    return _google_calendar_first_string(
        result,
        (
            "title",
            "summary",
        )
    )

def _google_calendar_extract_event_link(result):
    """
    Extract event link.
    """

    return _google_calendar_first_string(
        result,
        (
            "event_link",
            "eventLink",
            "htmlLink",
            "html_link",
            "link",
            "url",
        )
    )

async def _resolve_google_calendar_event_id(user_id, mcp_url, calendar_id, event_id=None, title=None, start_time=None, end_time=None, attendee_email=None):
    """
    Resolve an existing Google Calendar event ID.

    Priority:

        1. Explicit event ID
        2. Find event using title/date/attendee
        3. Return None if not uniquely identifiable
    """

    manager = get_zapier_manager()

    event_id = (
        str(event_id or "")
        .strip()
    )

    title = (
        str(title or "")
        .strip()
    )

    attendee_email = (
        str(attendee_email or "")
        .strip()
    )

    # --------------------------------------------------------
    # STEP 1
    # Explicit event ID
    # --------------------------------------------------------

    if event_id:

        print(
            "GOOGLE CALENDAR EVENT RESOLVE: "
            f"using supplied eventid={event_id}"
        )

        return {
            "status": "FOUND",
            "event_id": event_id
        }

    # --------------------------------------------------------
    # STEP 2
    # Search existing events
    # --------------------------------------------------------

    print(
        "GOOGLE CALENDAR EVENT RESOLVE: "
        "searching existing events"
    )

    find_params = {
        "calendarid": calendar_id,

        "expand_recurring": True,

        "output_hint": (
            "Return each matching event with "
            "event ID, title, start time, end time, "
            "attendees, and event link."
        )
    }

    if title:

        find_params["search_term"] = title

    if start_time:

        find_params["end_time"] = start_time

    if end_time:

        find_params["start_time"] = end_time

    if attendee_email:

        find_params["attendee_email"] = (
            attendee_email
        )

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name=GOOGLE_CALENDAR_FIND_TOOL,
            params=find_params
        )

        print(
            "=== GOOGLE CALENDAR FIND EVENT RESULT ==="
        )
        print(result)

        error = extract_zapier_error(result)

        if error:

            print(
                "GOOGLE CALENDAR FIND EVENT ERROR:",
                error
            )

            return {
                "status": "ERROR",
                "event_id": None,
                "message": (
                    "Unable to find the Google "
                    "Calendar event."
                ),
                "error": error
            }

        data = _google_calendar_extract_result(
            result
        )

        if not isinstance(data, dict):

            return {
                "status": "NOT_FOUND",
                "event_id": None,
                "message": (
                    "No usable event information "
                    "was returned."
                )
            }

        events = data.get("results")

        if events is None:

            events = []

        # Sometimes results may contain a single object.
        if isinstance(events, dict):

            events = [events]

        if not isinstance(events, list):

            events = []

        print(
            "GOOGLE CALENDAR EVENT RESOLVE: "
            f"found {len(events)} candidate events"
        )

        if not events:

            return {
                "status": "NOT_FOUND",
                "event_id": None,
                "message": (
                    "No matching Google Calendar "
                    "event was found."
                )
            }

        # ----------------------------------------------------
        # STEP 3
        # Extract candidates
        # ----------------------------------------------------

        candidates = []

        for event in events:

            if not isinstance(event, dict):
                continue

            candidate_id = (
                event.get("event_id")
                or event.get("eventId")
                or event.get("id")
            )

            if not candidate_id:
                continue

            candidates.append(event)

        if not candidates:

            return {
                "status": "NOT_FOUND",
                "event_id": None,
                "message": (
                    "Matching events were returned, "
                    "but no event ID was available."
                )
            }

        # ----------------------------------------------------
        # STEP 4
        # If exactly one candidate -> use it
        # ----------------------------------------------------

        if len(candidates) == 1:

            selected = candidates[0]

            selected_id = (
                selected.get("event_id")
                or selected.get("eventId")
                or selected.get("id")
            )

            print(
                "GOOGLE CALENDAR EVENT RESOLVE: "
                f"selected event={selected_id}"
            )

            return {
                "status": "FOUND",
                "event_id": str(selected_id),
                "event": selected
            }

        # ----------------------------------------------------
        # STEP 5
        # Try exact title matching
        # ----------------------------------------------------

        if title:

            normalized_title = (
                title.casefold()
                .strip()
            )

            exact_matches = []

            for event in candidates:

                event_title = (
                    event.get("title")
                    or event.get("summary")
                    or ""
                )

                if (
                    str(event_title)
                    .strip()
                    .casefold()
                    == normalized_title
                ):

                    exact_matches.append(event)

            if len(exact_matches) == 1:

                selected = exact_matches[0]

                selected_id = (
                    selected.get("event_id")
                    or selected.get("eventId")
                    or selected.get("id")
                )

                print(
                    "GOOGLE CALENDAR EVENT RESOLVE: "
                    "exact title match="
                    f"{selected_id}"
                )

                return {
                    "status": "FOUND",
                    "event_id": str(selected_id),
                    "event": selected
                }

            if len(exact_matches) > 1:

                return {
                    "status": "MULTIPLE",
                    "event_id": None,
                    "events": exact_matches,
                    "message": (
                        f'Multiple events named '
                        f'"{title}" were found.'
                    )
                }

        # ----------------------------------------------------
        # STEP 6
        # Ambiguous
        # ----------------------------------------------------

        return {
            "status": "MULTIPLE",
            "event_id": None,
            "events": candidates,
            "message": (
                "Multiple Google Calendar events "
                "matched the request."
            )
        }

    except Exception as e:

        print(
            "GOOGLE CALENDAR EVENT RESOLVE EXCEPTION:",
            str(e)
        )

        return {
            "status": "ERROR",
            "event_id": None,
            "message": (
                "Unable to resolve the Google "
                "Calendar event."
            ),
            "error": str(e)
        }

async def _update_google_calendar_event(*, user_id: str, mcp_url: str, params: dict,) -> dict:
    """
    Update an existing Google Calendar event using Zapier MCP.

    Required:
        eventid

    Optional:
        calendarid
        summary
        location
        description
        attendees
        visibility
        transparency
        all_day
        colorId
        start / start__dateTime
        end / end__dateTime
        recurrence_count
        recurrence_until
        recurrence_frequency
        reminders_methods
        reminders_minutes
        reminders__useDefault
        send_notifications
    """

    manager = get_zapier_manager()

    # ============================================================
    # INPUTS
    # ============================================================

    eventid = (
        params.get("eventid")
        or params.get("event_id")
        or ""
    )

    calendarid = (
        params.get("calendarid")
        or params.get("calendar_id")
        or ""
    )

    summary = params.get("summary")
    location = params.get("location")
    description = params.get("description")
    attendees = params.get("attendees")
    visibility = params.get("visibility")
    transparency = params.get("transparency")
    all_day = params.get("all_day")
    color_id = params.get("colorId")

    start = (
        params.get("start")
        or params.get("start_time")
        or params.get("start__dateTime")
    )

    end = (
        params.get("end")
        or params.get("end_time")
        or params.get("end__dateTime")
    )

    print("=" * 70)
    print("GOOGLE CALENDAR UPDATE EVENT")
    print("EVENT ID        :", eventid)
    print("CALENDAR ID     :", calendarid)
    print("SUMMARY         :", summary)
    print("LOCATION        :", location)
    print("START           :", start)
    print("END             :", end)
    print("ATTENDEES       :", attendees)
    print("DESCRIPTION     :", description)
    print("VISIBILITY      :", visibility)
    print("TRANSPARENCY    :", transparency)
    print("ALL DAY         :", all_day)
    print("COLOR ID        :", color_id)
    print("=" * 70)

    # ============================================================
    # VALIDATION
    # ============================================================

    if not eventid:
        return {
            "success": False,
            "status": "ERROR",
            "app": "google_calendar",
            "action": "update_event",
            "message": (
                "Event ID is required to update "
                "a Google Calendar event."
            ),
        }

    # ============================================================
    # RESOLVE CALENDAR
    # ============================================================

    resolved_calendar_id = calendarid

    if not resolved_calendar_id:

        print(
            "GOOGLE CALENDAR UPDATE EVENT: "
            "calendar not supplied; resolving default calendar"
        )

        try:
            calendar_result = await _resolve_google_calendar_id(
                user_id=user_id,
                mcp_url=mcp_url,
                calendar_id=None,
            )

            print(
                "GOOGLE CALENDAR CALENDAR RESOLVE RESULT:",
                calendar_result
            )

            if isinstance(calendar_result, dict):
                resolved_calendar_id = (
                    calendar_result.get("calendarid")
                    or calendar_result.get("calendar_id")
                    or calendar_result.get("id")
                )
            else:
                resolved_calendar_id = calendar_result

        except Exception as e:

            print(
                "GOOGLE CALENDAR UPDATE CALENDAR RESOLVE ERROR:",
                str(e)
            )

            return {
                "success": False,
                "status": "ERROR",
                "app": "google_calendar",
                "action": "update_event",
                "message": (
                    "Unable to determine the default "
                    "Google Calendar."
                ),
                "error": str(e),
            }

    if isinstance(resolved_calendar_id, dict):
        resolved_calendar_id = (
            resolved_calendar_id.get("calendarid")
            or resolved_calendar_id.get("calendar_id")
            or resolved_calendar_id.get("id")
        )

    if not resolved_calendar_id:
        return {
            "success": False,
            "status": "ERROR",
            "app": "google_calendar",
            "action": "update_event",
            "message": (
                "Unable to determine the Google Calendar ID."
            ),
        }

    resolved_calendar_id = str(resolved_calendar_id)

    print(
        "GOOGLE CALENDAR UPDATE EVENT: "
        f"using calendarid='{resolved_calendar_id}'"
    )

    # ============================================================
    # BUILD ZAPIER PARAMETERS
    # ============================================================

    zapier_params = {
        "calendarid": resolved_calendar_id,
        "eventid": str(eventid),
        "output_hint": (
            "Return the updated Google Calendar event "
            "title, event ID, start time, end time, "
            "event link, description, location, "
            "and attendees if available."
        ),
    }

    # ============================================================
    # OPTIONAL FIELDS
    # ============================================================

    if summary is not None:
        zapier_params["summary"] = summary

    if location is not None:
        zapier_params["location"] = location

    if description is not None:
        zapier_params["description"] = description

    if attendees is not None:

        if isinstance(attendees, str):
            attendees = [
                email.strip()
                for email in attendees.split(",")
                if email.strip()
            ]

        if isinstance(attendees, list):
            zapier_params["attendees"] = attendees

    if visibility is not None:
        zapier_params["visibility"] = visibility

    if transparency is not None:
        zapier_params["transparency"] = transparency

    if all_day is not None:
        zapier_params["all_day"] = all_day

    if color_id is not None:
        zapier_params["colorId"] = color_id

    # ============================================================
    # DATE / TIME
    # ============================================================

    if start is not None:
        zapier_params["start__dateTime"] = start

    if end is not None:
        zapier_params["end__dateTime"] = end

    # ============================================================
    # RECURRENCE / REMINDERS
    # ============================================================

    optional_fields = [
        "recurrence_count",
        "recurrence_until",
        "reminders_methods",
        "reminders_minutes",
        "reminders__useDefault",
        "send_notifications",
        "recurrence_frequency",
    ]

    for field in optional_fields:

        if params.get(field) is not None:
            zapier_params[field] = params[field]

    zapier_params['send_notifications'] = True

    # ============================================================
    # LOG
    # ============================================================

    print(
        "GOOGLE CALENDAR UPDATE EVENT PARAMS:",
        zapier_params
    )

    # ============================================================
    # CALL ZAPIER MCP DIRECTLY
    # ============================================================

    try:

        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_calendar_update_event",
            params=zapier_params,
        )

    except Exception as e:

        print(
            "GOOGLE CALENDAR UPDATE EVENT EXCEPTION:",
            str(e)
        )

        return {
            "success": False,
            "status": "ERROR",
            "app": "google_calendar",
            "action": "update_event",
            "eventid": eventid,
            "calendarid": resolved_calendar_id,
            "message": (
                "Unable to update the Google Calendar event."
            ),
            "error": str(e),
        }

    print(
        "=== GOOGLE CALENDAR UPDATE EVENT RAW RESULT ==="
    )
    print(result)
    print(
        "=== END GOOGLE CALENDAR UPDATE EVENT RAW RESULT ==="
    )

    # ============================================================
    # DETECT ZAPIER ERROR
    # ============================================================

    error = extract_zapier_error(result)

    if error:

        print(
            "GOOGLE CALENDAR UPDATE EVENT ERROR:",
            error
        )

        return {
            "success": False,
            "status": "ERROR",
            "app": "google_calendar",
            "action": "update_event",
            "eventid": eventid,
            "calendarid": resolved_calendar_id,
            "message": (
                "Google Calendar event could not be updated."
            ),
            "error": error,
        }

    # ============================================================
    # SUCCESS
    # ============================================================

    print(
        "GOOGLE CALENDAR UPDATE EVENT: "
        "UPDATE OPERATION SUCCESSFUL"
    )

    return {
        "success": True,
        "status": "SUCCESS",
        "app": "google_calendar",
        "action": "update_event",
        "eventid": eventid,
        "calendarid": resolved_calendar_id,
        "result": result,
    }

async def _delete_google_calendar_event(*, user_id: str, mcp_url: str, params: dict,) -> dict:

    eventid = params.get("eventid")
    calendarid = params.get("calendarid")
    send_notifications = params.get("send_notifications")

    print("=" * 70)
    print("GOOGLE CALENDAR DELETE EVENT")
    print("EVENT ID             :", eventid)
    print("CALENDAR ID          :", calendarid)
    print("SEND NOTIFICATIONS   :", send_notifications)
    print("=" * 70)

    # ---------------------------------------------------------
    # Validate event ID
    # ---------------------------------------------------------
    if not eventid:
        return {
            "success": False,
            "error": "Event ID is required to delete a Google Calendar event."
        }

    # ---------------------------------------------------------
    # Resolve calendar
    # ---------------------------------------------------------
    resolved_calendar_id = calendarid

    if not resolved_calendar_id:
        print(
            "GOOGLE CALENDAR DELETE EVENT: "
            "calendar not supplied; resolving default calendar"
        )

        calendar_result = await _resolve_google_calendar(
            user_id=user_id,
            mcp_url=mcp_url,
            calendarid=None,
        )

        print(
            "GOOGLE CALENDAR CALENDAR RESOLVE RESULT:",
            calendar_result
        )

        if isinstance(calendar_result, dict):
            resolved_calendar_id = (
                calendar_result.get("calendarid")
                or calendar_result.get("calendar_id")
                or calendar_result.get("id")
            )
        else:
            resolved_calendar_id = calendar_result

    # ---------------------------------------------------------
    # Resolver may return an object.
    # Zapier requires calendarid to be a STRING.
    # ---------------------------------------------------------
    if isinstance(resolved_calendar_id, dict):
        resolved_calendar_id = (
            resolved_calendar_id.get("calendarid")
            or resolved_calendar_id.get("calendar_id")
            or resolved_calendar_id.get("id")
        )

    if not resolved_calendar_id:
        return {
            "success": False,
            "error": "Unable to determine Google Calendar ID."
        }

    resolved_calendar_id = str(resolved_calendar_id)

    print(
        "GOOGLE CALENDAR DELETE EVENT: "
        f"using calendarid='{resolved_calendar_id}'"
    )

    # ---------------------------------------------------------
    # Build Zapier parameters
    # ---------------------------------------------------------
    zapier_params = {
        "calendarid": resolved_calendar_id,
        "eventid": str(eventid),
        "send_notifications": True,
        "output_hint": (
            "Return confirmation that the Google Calendar event "
            "was deleted, including the event ID and event title if available."
        ),
    }

    if send_notifications is not None:
        zapier_params["send_notifications"] = send_notifications

    print(
        "GOOGLE CALENDAR DELETE EVENT PARAMS:",
        zapier_params
    )

    # ---------------------------------------------------------
    # Call Zapier MCP
    # ---------------------------------------------------------
    try:
        result = await manager.execute_tool(
            user_id=user_id,
            mcp_url=mcp_url,
            tool_name="google_calendar_delete_event",
            params=zapier_params,
        )

        print(
            "=== GOOGLE CALENDAR DELETE EVENT RAW RESULT ==="
        )
        print(result)
        print(
            "=== END GOOGLE CALENDAR DELETE EVENT RAW RESULT ==="
        )

        # -----------------------------------------------------
        # Handle MCP/Zapier error response
        # -----------------------------------------------------
        if isinstance(result, dict):

            if result.get("isError"):
                return {
                    "success": False,
                    "error": result.get("error")
                    or "Google Calendar delete operation failed.",
                    "raw_result": result,
                }

            if result.get("error"):
                return {
                    "success": False,
                    "error": result.get("error"),
                    "raw_result": result,
                }

        return {
            "success": True,
            "operation": "delete_event",
            "event_id": str(eventid),
            "calendar_id": resolved_calendar_id,
            "result": result,
        }

    except Exception as e:

        print(
            "GOOGLE CALENDAR DELETE EVENT EXCEPTION:",
            str(e)
        )

        return {
            "success": False,
            "error": str(e),
            "event_id": str(eventid),
            "calendar_id": resolved_calendar_id,
        }

# endregion

# Singleton manager
manager = get_zapier_manager()

async def _zapier_action_async(app: str, operation: str, params: dict):
    """
    Execute a Zapier action.

    Args:
        app:
            gmail
            google_docs
            google_sheets

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

    # Normalize Google Docs app name
    if app == "google_doc":
        app = "google_docs"

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

        # print("FINAL QUERY:", query)

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
        print("=== PROFILE NOT FOUND ===")
        return "Profile not found."

    mcp_url = profile.get("mcp_url")

    if not mcp_url:
        print("=== MCP URL NOT FOUND ===")
        return "Please connect your Zapier MCP account first."

    print("=== BEFORE GOOGLE DOC BRANCH ===")
    print(f"app={app}")
    print(f"operation={operation}")

    # ============================================================
    # GOOGLE DOCS - 
    # ============================================================

    if app == "google_docs":
        
        GOOGLE_DOC_HANDLERS = {
            "read_document": _read_google_doc,
            "find_document": _find_google_doc,
            "create_document": _create_google_doc,
            "append_text": _append_google_doc,
            "share_document": _share_google_doc,
            "replace_text": _replace_google_doc,
            "delete_document": _delete_google_doc,
        }

        handler = GOOGLE_DOC_HANDLERS.get(operation)

        if handler:

            if operation == "append_text":
                if "document_name" not in params and params.get("file"):
                    params["document_name"] = params["file"]

                if "content" not in params and params.get("text"):
                    params["content"] = params["text"]

            return await handler(user_id=user_id, mcp_url=mcp_url, params=params)

    # ============================================================
    # GOOGLE SHEETS - 
    # ============================================================

    if app == "google_sheets":
        
        GOOGLE_SHEET_HANDLERS = {
            "find_spreadsheet": _find_google_spreadsheet,
            "delete_spreadsheet": _delete_google_spreadsheet,
            "delete_worksheet": _delete_google_worksheet,
            "read_spreadsheet": _read_google_spreadsheet,
            "delete_spreadsheet_rows": _delete_google_sheet_rows,
            "create_spreadsheet": _create_google_spreadsheet,
            "append_row": _append_google_sheet_row,
            "calculate_spreadsheet": _calculate_google_spreadsheet,
            "update_row": _update_google_sheet_row,
            "share_spreadsheet": _share_google_spreadsheet,
        }

        handler = GOOGLE_SHEET_HANDLERS.get(operation)

        if handler:
            
            return await handler(user_id=user_id, mcp_url=mcp_url, params=params)

    # ============================================================
    # GOOGLE CALENDAR - 
    # ============================================================

    if app == "google_calendar":
        
        GOOGLE_CALENDAR_HANDLERS = {
            "create_event": _create_google_calendar_event,
            "list_events": _list_google_calendar_events,
            "update_event": _update_google_calendar_event,
            "delete_event": _delete_google_calendar_event,
        }

        handler = GOOGLE_CALENDAR_HANDLERS.get(operation)

        if handler:
            
            return await handler(user_id=user_id, mcp_url=mcp_url, params=params)

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

    # print("NORMALIZED PARAMS:", params)


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


def _zapier_action_sync(app: str,  operation: str, params: dict):
    """
    Synchronous wrapper for LangGraph ToolNode.
    """
    return async_to_sync(_zapier_action_async)(app, operation, params)


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
    GOOGLE DOCS
    --------------------------------------------------

    Use:

    app="google_docs"

    --------------------------------------------------
    READ GOOGLE DOC
    --------------------------------------------------

    Use:

    operation="read_document"

    when the user wants to:

    - read a Google Doc
    - show a Google Doc
    - get Google Doc contents
    - read document
    - summarize a Google Doc
    - inspect a Google Doc
    - find information in a Google Doc

    If the user provides a document name:

    params={
        "document_name": "My Report"
    }

    If the user provides a Google Doc ID:

    params={
        "document_id": "1AbCdEf..."
    }

    Examples:

    User:
    Read my Google Doc named "Monthly Report"

    Tool:

    app="google_docs"
    operation="read_document"
    params={
        "document_name": "Monthly Report"
    }

    User:
    Read Google Doc 1AbCdEf123456

    Tool:

    app="google_docs"
    operation="read_document"
    params={
        "document_id": "1AbCdEf123456"
    }

    --------------------------------------------------
    FIND GOOGLE DOC BY NAME
    --------------------------------------------------

    Use:

    operation="find_document"

    when the user wants to search for or locate
    a specific Google Doc by its name.

    Examples:

    - find my Google Doc named "Sales Report"
    - search for the "Weather Report" Google Doc
    - locate my "Monthly Sales Report" document
    - does a Google Doc named "Sales Report" exist?

    Tool:

    app="google_docs"
    operation="find_document"

    params={
        "document_name":"Sales Report"
    }

    The operation should return:

    - document_name
    - document_id
    - document_url
    - status

    If no matching document exists, return:

    status="NOT_FOUND"

    Do NOT create a document during a find operation.

    --------------------------------------------------
    CREATE GOOGLE DOC
    --------------------------------------------------

    Use:

    app="google_docs"

    operation="create_document"

    when the user wants to create a new Google Doc.

    Examples:

    User:
    Create a Google Doc named "Weather Report"

    Tool:

    app="google_docs"
    operation="create_document"
    params={
        "title":"Weather Report"
    }

    User:
    Create a Google Doc named "Weather Report" with this content:
    Today's weather is sunny.

    Tool:

    app="google_docs"
    operation="create_document"
    params={
        "title":"Weather Report",
        "content":"Today's weather is sunny."
    }

    IMPORTANT

    - Use the exact title supplied by the user.
    - Put the requested document text in the content parameter.
    - Do NOT use read_document.
    - Do NOT ask for a document ID when creating a new document.

    --------------------------------------------------
    APPEND GOOGLE DOC
    --------------------------------------------------

    Use:

    operation="append_text"

    when the user wants to add text to the end of an existing document.

    Example:

    app="google_docs"
    operation="append_text"
    params={
        "file":"My Document",
        "text":"New text",
        "newline":true
    }

    --------------------------------------------------
    GOOGLE DOCS - FIND AND REPLACE
    --------------------------------------------------

    Use:

    operation="replace_text"

    when the user wants to replace text inside
    an existing Google Doc.

    Examples:

    - replace John with David
    - change John to David in my Google Doc
    - find John and replace it with David
    - replace all occurrences of John with David

    Example:

    app="google_docs"
    operation="replace_text"

    params={
        "document_name":"Sales Report",
        "find_text":"John",
        "replace_text":"David",
        "match_case":false
    }

    If the Google Doc ID is already known:

    params={
        "document_id":"1AbCdEf...",
        "find_text":"John",
        "replace_text":"David",
        "match_case":false
    }

    IMPORTANT:

    - document_name may be used when the user gives a document name.
    - document_id may be used when the ID is already known.
    - find_text is the exact text to search for.
    - replace_text is the replacement text.
    - match_case=false means John, JOHN, john, etc. can match.
    - match_case=true means only the exact capitalization matches.
    - If replace_text is empty, the matching text is deleted.
    - This operation modifies the existing Google Doc.
    - Do NOT create a new document.

    --------------------------------------------------
    SHARE GOOGLE DOC
    --------------------------------------------------

    Use:

    app="google_docs"

    operation="share_document"

    when the user wants to:

    - share a Google Doc
    - give someone access to a Google Doc
    - share document with an email address
    - make a Google Doc public
    - change Google Doc sharing permissions
    - give someone viewer access
    - give someone editor access

    Example:

    User:
    Share Google Doc "Test Document" to "test8cs@gmail.com"

    Tool:

    app="google_docs"
    operation="share_document"
    params={
        "document_name": "Test Document",
        "email": "test8cs@gmail.com",
        "permission": "email",
        "role": "reader"
    }

    Example:

    User:
    Make "Test Document" public with view access

    Tool:

    app="google_docs"
    operation="share_document"
    params={
        "document_name": "Test Document",
        "permission": "anyone",
        "role": "reader"
    }

    IMPORTANT:

    - If document_name is provided, resolve the Google Doc ID before sharing.
    - Do not create a new document.
    - Do not use create_document.
    - Do not use append_text.
    - For email sharing, use the recipient email address supplied by the user.
    - For public sharing, use permission="anyone".
    - For email-specific sharing, use permission="email".
    - Viewer access should use role="reader".
    - Editor access should use role="writer".

    --------------------------------------------------
    DELETE GOOGLE DOC
    --------------------------------------------------

    Use:

    operation="delete_document"

    when the user explicitly wants to delete/remove a Google Doc.

    Examples:

    User:
    Delete my Google Doc "Test Document"

    Tool:

    app="google_docs"
    operation="delete_document"
    params={
        "document_name": "Test Document"
    }

    Or if the user provides the ID:

    app="google_docs"
    operation="delete_document"
    params={
        "document_id": "1AbCdEf..."
    }

    IMPORTANT

    - This deletes the Google Drive file containing the Google Doc.
    - Do not use replace_text.
    - Do not use find_and_replace.
    - Do not delete the document's contents.
    - Do not use the permanent-delete action unless the user explicitly requests permanent deletion.

    ============================================================
    GOOGLE SHEETS
    ============================================================

    Use:

    app="google_sheets"


    ============================================================
    GOOGLE SHEETS GENERAL RULES
    ============================================================

    The AI should understand natural-language requests and
    translate them into the appropriate Google Sheets operation.

    The AI should NOT expose internal implementation details
    to the user.

    Do NOT ask the user for:

    - spreadsheet_id
    - worksheet ID
    - dynamic_properties
    - Zapier internal IDs
    - Zapier dynamic property IDs

    unless the user explicitly provides such information and
    it is actually required.

    The backend is responsible for resolving:

    - spreadsheet IDs
    - worksheet names when possible
    - dynamic properties
    - Zapier-specific parameters

    The AI should normally provide human-readable values such as:

    - spreadsheet_name
    - worksheet
    - row
    - column names
    - values


    --------------------------------------------------
    GOOGLE SHEETS OPERATION SELECTION
    --------------------------------------------------

    Choose the Google Sheets operation based on the
    USER'S INTENT, not on exact keywords.

    The user does NOT need to use the technical operation
    name or a specific keyword.

    Understand the complete request before selecting the
    operation.

    Use the following rules:

    1. FIND

    Use find_spreadsheet when the user explicitly wants to
    find, locate, search for, or check the existence of a
    Google Spreadsheet.

    Examples:

    "Find my Sales spreadsheet"
    "Search for my Employees spreadsheet"
    "Locate the spreadsheet called Sales Report"

    2. DELETE SPREADSHEET

    Use delete_spreadsheet want to delete, remove, or permanently delete a Google Sheet/spreadsheet file.

    Examples:

    "Delete the spreadsheet Employee"
    "Delete Google Sheet Sales Report"
    "Remove the spreadsheet named Test Data"

    2. DELETE WORKSHEET

    Use delete_worksheet want to delete, remove, or permanently delete a worksheet, tab, or sheet tab inside a Google Sheets spreadsheet.

    Examples:

    "Delete worksheet "Sheet2" from Employee"
    "Delete the "Archive" sheet from Sales Report"
    "Remove the "Sheet2" tab from spreadsheet Employee"
    "Delete the worksheet named Temporary Data"

    3. READ

    Use read_spreadsheet when the user wants to see, read,
    retrieve, inspect, search, or look up EXISTING data.

    Examples:

    "Show Rahul's salary"
    "What is Rahul's salary?"
    "Find Rahul in the sheet"
    "Show all employees"
    "Read the Sales sheet"


    4. DELETE

    Use delete_spreadsheet_rows when the user wants to deletes one or more spreadsheet rows from a worksheet.

    Examples:

    "Delete row 5 from Employee."
    "Delete rows 3, 5 and 8 from Sales Report"
    "Delete rows from Employee where Name=Rahul"


    5. CREATE

    Use create_spreadsheet when the user wants to CREATE NEW sheet.

    Examples:

    "Create a sheet called Employee with columns EmpId, Name, Salary"
    "Create a sheet  named Sales"
    "Create Google Sheet Sales with columns Invoice No, Customer, Amount"


    6. APPEND

    Use append_row when the user wants to ADD or CREATE
    a NEW row/record.

    Examples:

    "Add Rahul to the sheet"
    "Create a new employee Rahul"
    "Insert John into the Employees sheet"
    "Add a new sales record"


    7. UPDATE

    Use update_row when the user wants to CHANGE,
    MODIFY, EDIT, CORRECT, REPLACE, or SET a value in
    an EXISTING row.

    The user does NOT need to use the word "update".

    Examples:

    "Update Rahul's salary to 50000"
    "Change Rahul's salary to 50000"
    "Set Rahul's salary to 50000"
    "Modify Rahul's salary to 50000"
    "Edit Rahul's salary"
    "Correct Rahul's salary"
    "Make Rahul's salary 50000"


    8. CALCULATE

    Use calculate_spreadsheet when the user wants to
    perform a mathematical calculation, aggregation,
    comparison, counting, filtering-based calculation,
    or other numerical analysis on spreadsheet data.

    Examples:

    "Calculate the total salary"

    "What is the average salary?"

    "What is the highest salary?"

    "Calculate the total sales"

    "Calculate Rahul's salary plus bonus"


    IMPORTANT:

    Do NOT select an operation simply because one keyword
    appears in the request.

    Determine the user's intended ACTION from the complete
    request.

    For example:

    "Change Rahul's salary to 50000"

    must be treated as UPDATE even though the user did
    not use the word "update".

    Likewise:

    "Add Rahul with salary 50000"

    must be treated as APPEND because the user is asking
    to create a NEW row.

    And:

    "What is Rahul's salary?"

    must be treated as READ because the user is only
    requesting existing information.


    9. SHARE

    Use share_spreadsheet when the user wants to Share Google Sheet.

    Examples:

    "Share Customer with john@example.com"
    "Make 'Test Sheet' public with view access"



    --------------------------------------------------
    APPEND VS UPDATE
    --------------------------------------------------

    This distinction is critical.

    APPEND means:

    CREATE A NEW ROW.

    UPDATE means:

    MODIFY AN EXISTING ROW.

    Examples:

    "Add Rahul with salary 50000"
        -> append_row

    "Create Rahul with salary 50000"
        -> append_row

    "Change Rahul's salary to 50000"
        -> update_row

    "Set Rahul's salary to 50000"
        -> update_row

    "Modify Rahul's salary to 50000"
        -> update_row


    ============================================================
    1. FIND SPREADSHEET
    ============================================================

    Use:

    app="google_sheets"

    operation="find_spreadsheet"

    when the user explicitly wants to find or locate a
    Google Spreadsheet.

    Examples:

    "Find my Sales Report spreadsheet"

    "Find the spreadsheet named Employees"

    "Search for my Google Sheet called Sales"


    IMPORTANT:

    For normal read, append, calculate, or update requests,
    do NOT call find_spreadsheet as a separate AI operation.

    The backend should resolve the spreadsheet automatically
    from spreadsheet_name.


    ============================================================
    2. Google Sheets — Delete Spreadsheet / Worksheet
    ============================================================

    The assistant supports deleting Google Sheets spreadsheets and worksheets.

    Deletion must be performed through the Google Sheets delete operation. Never simulate, assume, or claim that a deletion occurred without successfully executing the corresponding Google Sheets tool.

    ---

    #### 1. Delete an entire spreadsheet

    When the user explicitly asks to delete, remove, or permanently delete an entire Google Sheets spreadsheet/file, use:

        app = google_sheets
        operation = delete_spreadsheet

    Examples:

    - Delete the spreadsheet "Employee"
    - Delete Google Sheet "Sales Report"
    - Remove the spreadsheet named "Test Data"
    - Permanently delete the "Employee" spreadsheet

    Parameters:

    {
        "spreadsheet_name": "Employee"
    }

    If the spreadsheet ID is already known, it may be used:

    {
        "spreadsheet_id": "1xxxxxxxxxxxxxxxxxxxxxxxx"
    }

    IMPORTANT:

    - "Spreadsheet" means the entire Google Sheets file.
    - Deleting a spreadsheet deletes the entire spreadsheet and all worksheets/tabs inside it.
    - Do NOT use delete_worksheet when the user asks to delete the entire spreadsheet.
    - Do NOT use update_row, append_row, clear_row, clear_sheet, or any other operation as a substitute for deleting the spreadsheet.
    - Resolve the exact spreadsheet before deleting it.
    - Delete only the spreadsheet explicitly requested by the user.

    ---

    #### 2. Delete a worksheet / sheet tab

    When the user explicitly asks to delete a worksheet, sheet, tab, or sheet tab inside a spreadsheet, use:

        app = google_sheets
        operation = delete_worksheet

    Examples:

    - Delete worksheet "Sheet2" from Google Sheet "Customer"
    - Delete the "Archive" sheet from "Sales Report"
    - Remove the "Sheet2" tab from spreadsheet "Employee"
    - Delete the worksheet named "Temporary Data"

    Parameters:

    {
        "spreadsheet_name": "Customer",
        "worksheet": "Sheet2"
    }

    If the spreadsheet ID is already known:

    {
        "spreadsheet_id": "1xxxxxxxxxxxxxxxxxxxxxxxx",
        "worksheet": "Sheet2"
    }

    IMPORTANT:

    - "Worksheet", "sheet", "tab", and "sheet tab" mean a worksheet/tab INSIDE a spreadsheet.
    - Deleting a worksheet does NOT delete the entire spreadsheet.
    - Do NOT use delete_spreadsheet when the user asks to delete only a worksheet.
    - Do NOT use update_row, append_row, clear_row, clear_sheet, or any other operation as a substitute for deleting the worksheet.
    - Resolve the exact spreadsheet first.
    - Resolve the exact worksheet inside that spreadsheet.
    - Delete only the requested worksheet.
    - Never delete another worksheet as a substitute.
    - Never assume "Sheet1" is the requested worksheet unless the user explicitly requested "Sheet1".

    ---

    #### 3. Spreadsheet vs worksheet interpretation

    Interpret the user's request as follows:

    - "Delete spreadsheet" → delete_spreadsheet
    - "Delete Google Sheet 'Customer'" → delete_spreadsheet
    - "Delete spreadsheet named 'Customer'" → delete_spreadsheet
    - "Delete worksheet 'Sheet2'" → delete_worksheet
    - "Delete sheet 'Sheet2' from 'Customer'" → delete_worksheet
    - "Delete tab 'Sheet2' from 'Customer'" → delete_worksheet
    - "Remove Sheet2 from Customer" → delete_worksheet
    - "Delete the Customer spreadsheet" → delete_spreadsheet

    The phrase "Google Sheet" refers to the spreadsheet file when it is used as the name of the overall file.

    When a worksheet/tab is explicitly mentioned together with a spreadsheet name, the requested operation is delete_worksheet.

    Example:

    User:
        Delete worksheet named "Sheet2" from Google Sheet "Customer"

    Must be interpreted as:

        app = google_sheets
        operation = delete_worksheet

    with:

    {
        "spreadsheet_name": "Customer",
        "worksheet": "Sheet2"
    }

    ---

    #### 4. Explicit deletion commands do NOT require confirmation

    An explicit user command to delete a specifically identified spreadsheet or worksheet is sufficient authorization.

    Do NOT ask for confirmation merely because the operation is destructive.

    Examples:

    User:
        Delete worksheet named "Sheet2" from Google Sheet "Customer"

    Correct:
        Execute delete_worksheet immediately.

    Incorrect:
        "This action is permanent. Please confirm."

    User:
        Delete spreadsheet "Customer"

    Correct:
        Execute delete_spreadsheet immediately.

    Incorrect:
        "Are you sure you want to permanently delete it?"

    Only ask a clarification question when the target cannot be determined.

    Examples:

    User:
        Delete a worksheet.

    Correct:
        Ask which spreadsheet and worksheet should be deleted.

    User:
        Delete Sheet2.

    Correct:
        Ask which spreadsheet contains Sheet2 if the spreadsheet cannot be determined from context.

    User:
        Delete the Customer sheet.

    If it is unclear whether "Customer" refers to a spreadsheet or worksheet, ask for clarification.

    ---

    #### 5. Mandatory tool execution

    For every delete request, the assistant MUST execute the corresponding Google Sheets operation.

    Do NOT claim that the resource was deleted merely because the user requested deletion.

    The assistant must NOT respond with a successful deletion message unless the delete operation was actually executed and returned a successful result.

    For worksheet deletion:

        User request
            ↓
        operation = delete_worksheet
            ↓
        resolve spreadsheet
            ↓
        resolve worksheet
            ↓
        execute Google Sheets worksheet deletion
            ↓
        verify successful tool result
            ↓
        report success

    For spreadsheet deletion:

        User request
            ↓
        operation = delete_spreadsheet
            ↓
        resolve spreadsheet
            ↓
        execute Google Sheets spreadsheet deletion
            ↓
        verify successful tool result
            ↓
        report success

    ---

    #### 6. Success response rules

    A successful response may be returned ONLY when the corresponding Google Sheets delete tool reports success.

    For example, after successfully deleting a worksheet:

        The worksheet "Sheet2" has been successfully deleted from the "Customer" spreadsheet.

    After successfully deleting a spreadsheet:

        The spreadsheet "Customer" has been successfully deleted.

    Do NOT return a success response before the tool has executed.

    Do NOT infer success from:
    - the user's request,
    - the operation name,
    - a planned tool call,
    - a generated response,
    - or an AI assumption.

    ---

    #### 7. Error handling

    If the Google Sheets delete operation returns an error:

    - Do NOT claim the resource was deleted.
    - Return an appropriate error message based on the actual tool result.

    Example:

        The worksheet "Sheet2" could not be deleted from the "Customer" spreadsheet.

    If the spreadsheet cannot be found:

        The spreadsheet "Customer" could not be found.

    If the worksheet cannot be found:

        The worksheet "Sheet2" could not be found in the "Customer" spreadsheet.

    If the delete operation fails for any other reason:

        The worksheet "Sheet2" could not be deleted from the "Customer" spreadsheet.

    Do not fabricate a successful deletion.

    ---

    #### 8. Never substitute another Google Sheets operation

    When the requested operation is deletion:

        delete_spreadsheet
        or
        delete_worksheet

    must be used.

    Never substitute:

        update_row
        append_row
        create_spreadsheet
        clear_row
        clear_sheet
        read_spreadsheet

    for a delete operation.

    Reading a spreadsheet is allowed only when necessary to resolve or verify the requested target.

    ---

    #### 9. Exact operation mapping

    Use these operation names:

        delete_spreadsheet
        delete_worksheet

    The backend is responsible for mapping these operations to the corresponding Zapier/MCP Google Sheets tools.

    The assistant must not invent a different operation name.

    ---

    #### 10. Critical rule

    NEVER say that a spreadsheet or worksheet was successfully deleted unless the corresponding delete operation was actually executed and returned a successful result.

    A planned deletion is NOT a completed deletion.

    A tool-selection decision is NOT a completed deletion.

    A generated confirmation is NOT a completed deletion.

    Only a successful Google Sheets delete-tool result means the deletion actually occurred.


    ============================================================
    3. READ GOOGLE SHEET
    ============================================================

    Use:

    app="google_sheets"

    operation="read_spreadsheet"

    when the user wants to view, retrieve, search, inspect,
    or look up existing spreadsheet data.

    Examples:

    "Read my Sales Report"

    "Show me the Employees sheet"

    "Show rows 2 to 100"

    "What is Rahul's salary?"

    "Find Rahul in the Employees sheet"

    "Find the row where Email is john@example.com"

    "Show all sales for John"

    "Get all rows where Status is Pending"


    The AI should provide, when known:

    spreadsheet_name

    worksheet

    first_row

    row_count

    batch_size


    Example:

    User:
    "Read my Sales Report spreadsheet."

    Tool:

    app="google_sheets"

    operation="read_spreadsheet"

    params={
        "spreadsheet_name": "Sales Report"
    }


    Example:

    User:
    "Read rows 2 to 500 from the Sales worksheet."

    Tool:

    app="google_sheets"

    operation="read_spreadsheet"

    params={
        "spreadsheet_name": "Sales Report",
        "worksheet": "Sales",
        "first_row": 2,
        "row_count": 499
    }


    ------------------------------------------------------------
    READ / SEARCH INTENT
    ------------------------------------------------------------

    Use read_spreadsheet when the user wants to:

    - view data
    - retrieve data
    - inspect records
    - find information
    - search rows
    - look up values
    - check existing values

    Do NOT use update_row simply because the user mentions
    a person and a column.

    For example:

    "What is Rahul's salary?"

    means READ, not UPDATE.

    ============================================================
    4. GOOGLE SHEETS DELETE ROW(S)
    ============================================================

    Use:

    app="google_sheets"

    operation="delete_spreadsheet_rows"

    When the user asks to delete row(s) from a Google Spreadsheet, use
    the `delete_sheet_rows` operation.

    The operation supports TWO deletion modes:

    1. EXPLICIT ROW DELETION

    Use when the user specifies row numbers, indexes, or ranges.

    Examples:

    - "Delete row 5"
    - "Delete rows 2 and 7"
    - "Delete rows 3-6"
    - "Delete rows 2,4,8"
    - "Delete rows 3 through 10"

    Pass the requested row numbers/ranges in `rows`.

    2. CONDITION-BASED ROW DELETION

    Use when the user specifies a condition describing which rows
    should be deleted.

    Examples:

    - "Delete employees whose salary is greater than 50000"
    - "Delete rows where Salary > 50000"
    - "Delete employees where Department is HR"
    - "Delete rows where Status is inactive"
    - "Delete customers whose Age is less than 18"

    For condition-based deletion, provide:

    condition = {
        "column": "<column/header name>",
        "operator": "<operator>",
        "value": "<comparison value>"
    }

    Supported operators include:

    - =
    - ==
    - !=
    - >
    - >=
    - <
    - <=
    - contains
    - starts_with
    - ends_with
    - is_empty
    - is_not_empty

    IMPORTANT:

    The underlying Zapier delete-row tool accepts row numbers, not
    conditions.

    Therefore, for condition-based deletion, the backend must first
    read the worksheet, evaluate the condition against the worksheet
    data, determine the actual Google Sheet row numbers, and then pass
    those row numbers to the Zapier delete-row tool.

    Do NOT attempt to send the condition directly to the Zapier
    delete-row tool.

    ### WORKSHEET IS OPTIONAL

    For `delete_sheet_rows`, the worksheet parameter is OPTIONAL.

    If the user specifies a worksheet:

        "Delete rows where Salary > 50000 from Sheet2"

    use:

        worksheet = "Sheet2"

    If the user does NOT specify a worksheet:

        "Delete rows where Salary > 50000 from Employee"

    do NOT ask the user to provide a worksheet.

    Instead, the backend must use the FIRST/default worksheet in the
    spreadsheet.

    ### ROW NUMBERING

    Google Sheets row numbers are 1-based.

    The header row is row 1.

    Therefore:

        first data row = row 2
        second data row = row 3
        etc.

    When deleting multiple rows, the backend must delete rows from
    highest row number to lowest row number so that deleting one row
    does not shift the remaining target rows.

    ### DO NOT CONFUSE ROW DELETION WITH WORKSHEET DELETION

    "Delete row 5"
        → delete_sheet_rows

    "Delete rows where Salary > 50000"
        → delete_sheet_rows

    "Delete Sheet2"
        → delete_worksheet

    "Delete the Customer spreadsheet"
        → delete_spreadsheet

    Never use delete_worksheet when the user asks to delete rows.
    Never use delete_spreadsheet when the user asks to delete rows.

    ============================================================
    6. APPEND GOOGLE SHEET ROW
    ============================================================

    Use:

    app="google_sheets"

    operation="append_row"

    when the user wants to CREATE or ADD a NEW row.

    Examples:

    "Add Rahul to Employees"

    "Create a new employee named Rahul"

    "Add John, john@example.com and 500 to Sales Report"

    "Insert a new sales record"

    "Create a new row for Amit"

    "Add this customer to the sheet"


    The AI should provide:

    spreadsheet_name

    worksheet (only when explicitly known/requested)

    row


    Example:

    User:
    "Add John, john@example.com and 500 to my Sales Report."

    Tool:

    app="google_sheets"

    operation="append_row"

    params={
        "spreadsheet_name": "Sales Report",
        "row": {
            "Name": "John",
            "Email": "john@example.com",
            "Amount": 500
        }
    }


    If the user specifies a worksheet:

    params={
        "spreadsheet_name": "Sales Report",
        "worksheet": "Sales",
        "row": {
            "Name": "John",
            "Email": "john@example.com",
            "Amount": 500
        }
    }


    IMPORTANT:

    Do NOT call find_spreadsheet as a separate AI operation.

    The backend resolves the spreadsheet automatically.

    Do NOT invent:

    - spreadsheet IDs
    - worksheet IDs
    - dynamic_properties

    The backend resolves dynamic_properties using the
    Google Sheets dynamic-property schema.

    If the spreadsheet does not exist, follow the backend's
    existing spreadsheet creation behavior.

    If the worksheet does not exist, follow the backend's
    existing worksheet creation behavior.


    ------------------------------------------------------------
    APPEND VS UPDATE
    ------------------------------------------------------------

    This distinction is very important.

    If the user wants to ADD a NEW record:

    use append_row.

    Examples:

    "Add Rahul"

    "Create Rahul"

    "Insert Rahul"

    "Add a new employee Rahul"


    If the user wants to MODIFY an EXISTING record:

    use update_row.

    Examples:

    "Change Rahul's salary to 50000"

    "Update Rahul's salary to 50000"

    "Set Rahul's salary to 50000"

    "Modify Rahul's salary to 50000"

    ============================================================
    7. UPDATE GOOGLE SHEET ROW
    ============================================================

    Use:

    app="google_sheets"

    operation="update_row"

    when the user wants to MODIFY an EXISTING row.

    The user does NOT need to use the word "update".

    The following natural-language expressions can
    represent UPDATE intent:

    - update
    - change
    - modify
    - edit
    - alter
    - replace
    - correct
    - fix
    - set
    - make ... equal to
    - make ... ...
    - change ... to ...
    - change ... from ... to ...


    --------------------------------------------------
    UPDATE EXAMPLES
    --------------------------------------------------

    User:

    "Update Rahul's salary to 50000"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",
        "find": {
            "column": "Name",
            "value": "Rahul"
        },
        "updates": {
            "Salary": 50000
        }
    }


    User:

    "Change Rahul's salary to 50000"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",
        "find": {
            "column": "Name",
            "value": "Rahul"
        },
        "updates": {
            "Salary": 50000
        }
    }


    User:

    "Set Rahul's salary to 50000"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",
        "find": {
            "column": "Name",
            "value": "Rahul"
        },
        "updates": {
            "Salary": 50000
        }
    }


    User:

    "Make Rahul's salary 50000"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",
        "find": {
            "column": "Name",
            "value": "Rahul"
        },
        "updates": {
            "Salary": 50000
        }
    }


    --------------------------------------------------
    UPDATE BY ROW NUMBER
    --------------------------------------------------

    If the user explicitly provides a row number,
    use row_number.

    Example:

    "Change the salary in row 7 to 50000"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",
        "row_number": 7,
        "updates": {
            "Salary": 50000
        }
    }

    Do NOT invent a row number.


    --------------------------------------------------
    UPDATE BY FIND
    --------------------------------------------------

    If the user identifies an existing row by a value,
    use:

    find={
        "column": "...",
        "value": "..."
    }


    Example:

    "Change Rahul's salary to 50000"

    Use:

    find={
        "column": "Name",
        "value": "Rahul"
    }


    The backend will locate the matching row.


    --------------------------------------------------
    MULTIPLE COLUMN UPDATE
    --------------------------------------------------

    If the user wants to change multiple values in the
    same existing row, put all requested changes inside
    updates.

    Example:

    "Change Rahul's salary to 50000 and status to Active"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",
        "find": {
            "column": "Name",
            "value": "Rahul"
        },
        "updates": {
            "Salary": 50000,
            "Status": "Active"
        }
    }

    Only update the columns explicitly requested by the
    user.

    Do NOT modify unrelated columns.


    --------------------------------------------------
    OLD VALUE SAFETY CONDITION
    --------------------------------------------------

    If the user explicitly provides both the OLD value
    and the NEW value, preserve the old value as a
    condition.

    Example:

    "Change Rahul's salary from 45000 to 50000"

    Tool:

    app="google_sheets"

    operation="update_row"

    params={
        "spreadsheet_name": "Employees",

        "find": {
            "column": "Name",
            "value": "Rahul"
        },

        "condition": {
            "column": "Salary",
            "value": 45000
        },

        "updates": {
            "Salary": 50000
        }
    }


    The backend must verify the current value before
    performing the update.

    If the current value is not 45000:

    - do NOT update the row
    - return a condition failure


    If the user does NOT provide an old value:

    DO NOT invent one.

    DO NOT create a condition.


    --------------------------------------------------
    MULTIPLE MATCH PROTECTION
    --------------------------------------------------

    If the find condition matches multiple rows,
    do NOT arbitrarily update the first row.

    Do NOT guess which row the user means.

    Return a multiple-match result and ask the user
    for a more specific identifier.

    Possible identifiers include:

    - employee ID
    - email
    - row number
    - another unique column


    Example:

    "Change John's salary to 50000"

    If multiple rows have:

    Name = John

    do NOT choose the first John.


    --------------------------------------------------
    UPDATE SAFETY
    --------------------------------------------------

    Never invent:

    - row_number
    - spreadsheet_id
    - worksheet ID
    - column names
    - existing values

    Only modify values explicitly requested by the user.

    Do not modify unrelated columns.

    Do not append a new row when the user intends to
    modify an existing row.


    --------------------------------------------------
    DYNAMIC PROPERTIES
    --------------------------------------------------

    The AI should provide normal spreadsheet column names
    inside updates.

    Example:

    updates={
        "Salary": 50000,
        "Status": "Active"
    }

    Do NOT generate Zapier dynamic_properties.

    The backend resolves dynamic_properties using the
    Google Sheets schema.


    --------------------------------------------------
    IMPORTANT UPDATE INTENT RULE
    --------------------------------------------------

    Do not require the exact word "update".

    These requests all mean UPDATE:

    "Update Rahul salary to 50000"

    "Change Rahul salary to 50000"

    "Modify Rahul salary to 50000"

    "Set Rahul salary to 50000"

    "Make Rahul salary 50000"

    "Correct Rahul salary to 50000"

    "Change Rahul salary from 45000 to 50000"

    
    ============================================================
    8. GOOGLE SHEETS CALCULATIONS
    ============================================================

    Use:

    app="google_sheets"

    operation="calculate_spreadsheet"

    when the user wants to perform a calculation,
    aggregation, comparison, filtering-based calculation,
    or mathematical analysis on Google Sheets data.

    Examples:

    "Calculate the total sales"

    "What is the average salary?"

    "Find the highest salary"

    "Find the lowest salary"

    "Calculate the total revenue"

    "Calculate the average sales for John"

    "Calculate revenue minus expenses"

    "What percentage of orders were refunded?"

    "Count the number of employees"

    "Calculate the sum of Amount"

    "Find the average Amount where Status is Completed"


    IMPORTANT:

    The calculation is performed by the backend's
    AI-powered calculation engine.

    The AI should NOT try to calculate the final result
    itself when the request requires spreadsheet data.

    The AI should pass the user's intended calculation
    to the calculation operation.

    --------------------------------------------------
    CALCULATION TOOL CALL RULE
    --------------------------------------------------

    For a calculation request, call:

    operation="calculate_spreadsheet"

    The calculation operation is self-contained.

    The backend will:

    1. Resolve the spreadsheet.
    2. Read the required spreadsheet data.
    3. Pass the data to the AI calculation engine.
    4. Perform the requested calculation.
    5. Return the calculation result.

    Therefore:

    DO NOT call read_spreadsheet before calculate_spreadsheet.

    DO NOT call read_spreadsheet after calculate_spreadsheet
    when calculate_spreadsheet returns SUCCESS.

    The result returned by calculate_spreadsheet must be
    treated as the authoritative result for the requested
    calculation.

    After a successful calculate_spreadsheet call:

    - use its result to answer the user
    - do not repeat the calculation
    - do not call read_spreadsheet to verify the result
    - do not call calculate_spreadsheet again for the same
    calculation unless the first calculation failed or
    the user explicitly requested another calculation.


    --------------------------------------------------
    MULTIPLE CALCULATIONS IN ONE USER REQUEST
    --------------------------------------------------

    If the user asks for multiple calculations on the same
    spreadsheet data, prefer ONE calculate_spreadsheet
    operation containing the complete natural-language
    calculation request.

    Example:

    User:

    "How many laptops are there and what is the total
    quantity of laptops?"

    Prefer:

    app="google_sheets"

    operation="calculate_spreadsheet"

    params={
        "spreadsheet_name": "Sales Report",
        "calculation_request":
            "Count the number of rows where Product is Laptop,
            and calculate the total Quantity where Product is Laptop."
    }

    Do NOT make separate calls:

    calculate_spreadsheet -> count

    followed by:

    calculate_spreadsheet -> sum

    when both calculations belong to the same user request.

    The backend calculation engine should perform all
    requested calculations from the same spreadsheet read.

    --------------------------------------------------
    CALCULATION PARAMETERS
    --------------------------------------------------

    For calculate_spreadsheet, normally provide only:

    - spreadsheet_name
    - spreadsheet_id, only if explicitly available
    - worksheet, only when known
    - calculation_request

    The calculation_request must contain the user's
    complete natural-language calculation requirement.

    The AI should NOT construct separate calculation
    parameters such as:

    - function
    - column
    - filters
    - distinct

    for the calculation engine.

    The backend AI calculation engine will determine:

    - the required operation
    - the required columns
    - filters
    - aggregation
    - mathematical expression
    - comparisons
    - multiple calculations

    from calculation_request.


    Example:

    User:

    "Calculate the total Amount in Sales Report."

    Tool:

    app="google_sheets"

    operation="calculate_spreadsheet"

    params={
        "spreadsheet_name": "Sales Report",
        "calculation_request":
            "Calculate the total Amount."
    }


    Example:

    User:

    "Calculate the average salary of active employees."

    Tool:

    app="google_sheets"

    operation="calculate_spreadsheet"

    params={
        "spreadsheet_name": "Employees",
        "calculation_request":
            "Calculate the average Salary for employees
            where Status is Active."
    }


    Example:

    User:

    "How many laptops are there and what is the total
    quantity of laptops?"

    Tool:

    app="google_sheets"

    operation="calculate_spreadsheet"

    params={
        "spreadsheet_name": "Sales Report",
        "calculation_request":
            "Count the rows where Product is Laptop and
            calculate the total Quantity for those rows."
    }


    IMPORTANT:

    Do NOT hardcode separate Python logic for every
    mathematical function in the AI prompt.

    The backend calculation engine handles the calculation.

    ============================================================
    9. GOOGLE SHEETS SHARING:
    ============================================================

    - A Google Spreadsheet is a Google Drive file.
    - To share a Google Spreadsheet, use the
    google_drive_add_file_sharing_preference Zapier action.
    - Do NOT search for or invent a separate Google Sheets sharing action.

    When the user asks to share a Google Spreadsheet:

    1. Resolve the spreadsheet name to its Google Drive file ID.
    2. Determine the requested sharing scope.
    3. Use the appropriate permission value.

    Supported permission values:

    - email
    - public_link_view
    - public_link_edit
    - public_link_comment
    - public_discoverable
    - org_link_view
    - org_link_edit
    - org_link_comment
    - org_discoverable

    For sharing with a specific person:

    - permission = "email"
    - email is required.
    - If the user requests view/read access, use role = "reader".
    - If the user requests edit access, use role = "writer".
    - If the user requests comment access, use role = "commenter".

    Examples:

    "Share Customer with john@example.com"
    → permission = "email"
    → email = "john@example.com"

    "Give john@example.com edit access to Customer"
    → permission = "email"
    → email = "john@example.com"
    → role = "writer"

    "Share Customer with anyone who has the link"
    → permission = "public_link_view"

    "Make Customer editable by anyone with the link"
    → permission = "public_link_edit"

    "Make Customer viewable by anyone with the link"
    → permission = "public_link_view"

    IMPORTANT:

    - Do not remove existing sharing permissions.
    - google_drive_add_file_sharing_preference adds a sharing scope.
    - Do not claim that existing permissions were removed or replaced.
    - Return the sharing URL when Zapier provides one.


    ============================================================
    GOOGLE WORKSPACE SHARING ARCHITECTURE:
    ============================================================

    Google Docs and Google Sheets use the same Google Drive
    sharing mechanism.

    Both are Google Drive files.

    Therefore:

    Google Docs
        -> google_drive_add_file_sharing_preference

    Google Sheets
        -> google_drive_add_file_sharing_preference

    Do NOT create or search for separate sharing actions for
    Google Docs or Google Sheets.

    When sharing either type of file:

    1. Resolve the file name to its Google Drive file ID.
    2. Determine the requested sharing permission.
    3. For a specific email address:
        permission = "email"
    4. For link sharing:
        public_link_view
        public_link_edit
        public_link_comment
    5. For organization sharing:
        org_link_view
        org_link_edit
        org_link_comment
        org_discoverable

    For email sharing:

        view/read  -> role = "reader"
        edit       -> role = "writer"
        comment    -> role = "commenter"

    IMPORTANT:

    - Sharing adds a sharing scope.
    - It does NOT remove existing sharing permissions.
    - Never claim that existing permissions were replaced.
    - Return the sharing URL when available.
    - The backend centralizes the actual Google Drive sharing
    implementation.
    - Do not implement separate sharing logic for Docs and Sheets.


    ==============================
    GOOGLE CALENDAR
    ==============================

    The assistant can create Google Calendar events using
    Zapier MCP.

    Supported operation:

    - create_event
    - list_events

    Zapier MCP tool:

    google_calendar_create_detailed_event


    CREATE EVENT
    ------------

    When the user asks to create, schedule, add, or put an event
    on Google Calendar, use:

    operation = create_event


    Required information:

    - title
    - start
    - end


    Parameter mapping:

    User title
        -> summary

    User start date/time
        -> start__dateTime

    User end date/time
        -> end__dateTime


    Example:

    User:
    "Create a meeting tomorrow from 10 AM to 11 AM called
    Team Meeting."

    The AI should construct:

    {
        "title": "Team Meeting",
        "start": "<resolved ISO datetime>",
        "end": "<resolved ISO datetime>"
    }


    DATETIME RULES
    --------------

    The Google Calendar create-event tool expects ISO 8601
    date-time values.

    Use:

    YYYY-MM-DDTHH:MM:SS±HH:MM

    or UTC:

    YYYY-MM-DDTHH:MM:SSZ


    When the user provides a date/time without a timezone,
    use the user's configured/local timezone when available.

    Do not invent a timezone if the user's timezone is genuinely
    unknown.


    CALENDAR
    --------

    calendarid is optional.

    If the user does not specify a calendar, do NOT ask for a
    calendar unnecessarily.

    Use the connected/default Google Calendar.

    If the user explicitly specifies a calendar, pass the
    calendar identifier/name as calendarid as appropriate.

    ATTENDEES
    ---------

    If the user says that an event is "with" a person,
    this normally indicates that the person should be an attendee.

    Example:

    "Create a meeting with Vinayak"

    means:

    attendee = Vinayak

    However, an attendee email address is required to send
    the invitation.

    If the person's email address is already known from the
    conversation or application context, use it.

    If the person's email address is not known, ask the user:

    "What is Vinayak's email address?"

    Do not invent an email address.

    Do not claim that an invitation was sent unless the
    attendee was actually supplied to the Google Calendar
    create-event operation.

    OPTIONAL EVENT FIELDS
    ---------------------

    The following may also be supplied when the user requests
    them:

    description
    location
    attendees


    Attendees should be passed as a list of email addresses.

    Example:

    {
        "attendees": [
            "john@example.com",
            "mary@example.com"
        ]
    }


    STANDARD EVENTS
    ---------------

    For normal events use:

    eventType = "default"


    Do not use outOfOffice unless the user explicitly requests
    an out-of-office event.


    IMPORTANT EXECUTION RULE
    ------------------------

    Creating an event is a write operation.

    Once the required information is available, call
    google_calendar_create_detailed_event exactly once.

    Do not call another Google Calendar create-event action for
    the same user request.

    Do not create duplicate events because of uncertainty in the
    response.

    If the Zapier MCP call succeeds, return the success result.

    If Zapier/MCP returns an explicit error, report that the event
    could not be created and include the relevant error.

    Do not claim an event was created if the Zapier/MCP operation
    failed.


    MISSING INFORMATION
    -------------------

    If title is missing, ask for the event title.

    If start is missing, ask for the event start date/time.

    If end is missing, ask for the event end date/time.

    Do not guess missing event times.


    NATURAL LANGUAGE DATETIME
    -------------------------

    The AI may interpret natural language such as:

    "tomorrow at 10 AM"
    "Friday at 3 PM"
    "August 30 at 2 PM"
    "next Monday from 10 AM to 11 AM"

    and convert it to the required ISO 8601 date-time format.

    When relative dates are used, resolve them using the current
    date/time and user's timezone.


    SUCCESS RESPONSE
    ----------------

    After successful creation, respond concisely.

    Example:

    "Calendar event 'Team Meeting' was created successfully
    for August 28, 2026 from 10:00 AM to 11:00 AM."


    ERROR RESPONSE
    --------------

    If creation fails:

    "The calendar event could not be created."

    Do not state that the event was created when the MCP action
    failed.

    TIMEZONE RULES:
    ---------------

    1. Interpret user-provided times in the user's local timezone unless
    the user explicitly specifies another timezone.

    2. For users in India, use:
        Asia/Kolkata
        UTC+05:30

    3. When creating an event, ALWAYS preserve the intended local time.
    For example:

        User: "Create a meeting tomorrow from 10 AM to 11 AM."

    means:

        10:00 AM Asia/Kolkata
        11:00 AM Asia/Kolkata

    4. Do not reinterpret 10 AM as UTC.

    5. When constructing ISO-8601 datetime values, include the timezone
    offset, e.g.:

        2026-08-28T10:00:00+05:30

    6. If the Calendar tool supports an explicit timezone field, ALWAYS
    pass:

        Asia/Kolkata

    7. Never change the user's requested clock time merely because the
    datetime is converted internally to UTC.



    ------------------------------------------------------------
    GOOGLE CALENDAR — LIST EVENTS
    ------------------------------------------------------------

    Use operation:

        list_events

    to retrieve events from the user's Google Calendar.

    Use it for requests such as:

    - "Show my calendar"
    - "What meetings do I have today?"
    - "What events do I have tomorrow?"
    - "Show my events this week"
    - "Find my Team Meeting"
    - "Show meetings with Vinayak"
    - "Do I have anything scheduled at 10 AM?"
    - "What meetings are coming up?"

    The underlying Zapier MCP tool is:

        google_calendar_find_events

    IMPORTANT TIME BOUNDARY RULE:

    The Zapier tool uses unusual parameter names:

        end_time = LOWER boundary / EARLIEST timestamp

        start_time = UPPER boundary / LATEST timestamp

    Therefore:

    For events from:
        August 28 00:00
    to:
        August 28 23:59

    send:

        end_time   = August 28 00:00
        start_time = August 28 23:59

    DO NOT reverse these values.

    ------------------------------------------------------------
    DATE/TIME INTERPRETATION
    ------------------------------------------------------------

    Interpret natural-language dates using the user's local
    timezone.

    Examples:

    "today"
        -> today 00:00 through today 23:59:59

    "tomorrow"
        -> tomorrow 00:00 through tomorrow 23:59:59

    "this week"
        -> beginning of the current week through the end of
        the current week

    "next week"
        -> beginning of next week through the end of next week

    "upcoming events"
        -> use the current time as the lower boundary and a
        reasonable future upper boundary.

    Always send valid ISO-8601 date-time values to Zapier.

    ------------------------------------------------------------
    CALENDAR SELECTION
    ------------------------------------------------------------

    If the user does not specify a calendar:

        Use the user's default/personal Google Calendar.

    The calendar ID is a Zapier dynamic enum.

    Do NOT invent a calendar ID.

    Do NOT assume a calendar name is the calendar ID.

    When necessary, call:

        list_dynamic_enum_values

    with:

        tool_name = "google_calendar_find_events"
        property_name = "calendarid"

    and use one of the returned valid values.

    Never select a calendar whose name contains "Birthdays"
    when choosing the default calendar.

    ------------------------------------------------------------
    EVENT SEARCH
    ------------------------------------------------------------

    Only use search_term when the user explicitly asks to search
    for/filter events by words in the event title or description.

    Examples:

    "Find my Team Meeting"
        -> search_term = "Team Meeting"

    "Show events about project review"
        -> search_term = "project review"

    Do not unnecessarily populate search_term for a general
    calendar listing.

    ------------------------------------------------------------
    ATTENDEE SEARCH
    ------------------------------------------------------------

    If the user explicitly asks for events involving a specific
    email address, use:

        attendee_email

    Example:

    "Show meetings with test8cs@gmail.com"

    Use:

        attendee_email = "test8cs@gmail.com"

    Do not use attendee_email when the user only provides a
    person's name and no email address.

    ------------------------------------------------------------
    EVENT TYPES
    ------------------------------------------------------------

    Leave eventTypes empty unless the user explicitly asks to
    filter by event type.

    Supported event types include:

        birthday
        default
        focusTime
        fromGmail
        outOfOffice
        workingLocation

    ------------------------------------------------------------
    RECURRING EVENTS
    ------------------------------------------------------------

    By default, expand recurring events.

    When:

        expand_recurring = true

    recurring events are returned as individual occurrences.

    Do not change this unless the user explicitly asks for the
    recurring event series rather than individual occurrences.

    ------------------------------------------------------------
    ORDERING
    ------------------------------------------------------------

    For normal calendar listings use:

        ordering = "startTime"

    This returns events ordered by start time.

    Use:

        ordering = "updated"

    only when the user specifically asks for recently modified
    or updated events.

    ------------------------------------------------------------
    PAGINATION
    ------------------------------------------------------------

    The Google Calendar search tool can return up to 250 matching
    events.

    If the response contains a paging_token:

        pass the exact returned paging_token back to
        google_calendar_find_events

    when additional results are required.

    Never invent or modify a paging_token.

    ------------------------------------------------------------
    OUTPUT
    ------------------------------------------------------------

    When listing events, present useful information such as:

    - Event title
    - Date
    - Start time
    - End time
    - Location, if available
    - Attendees, if available
    - Event link, if available

    Do not claim that events exist unless the Zapier tool actually
    returned them.

    If no events are returned, clearly say that no matching events
    were found.

    Do not fabricate event IDs, links, attendees, locations,
    dates, or times.


    ------------------------------------------------------------
    GOOGLE CALENDAR — UPDATE EVENT
    ------------------------------------------------------------

    You can update an existing Google Calendar event using:

    Operation:
        update_event

    Zapier tool:
        google_calendar_update_event


    UPDATE EVENT RULES:

    1. Use update_event when the user wants to modify an existing
    Google Calendar event.

    2. The event must be identified before updating it.

    3. If the user provides an event ID, use that event ID directly.

    4. If the user does NOT provide an event ID:
    - Identify the event using the available calendar information.
    - Use the event title, date, time, attendee, or other information
        provided by the user to find the correct event.
    - Resolve the calendar and event ID before performing the update.

    5. Do NOT update an event until the target event has been identified
    with sufficient confidence.

    6. If multiple events could match the user's description, do not
    arbitrarily choose one. Ask the user to clarify which event they
    mean.

    7. Only update fields explicitly requested by the user.

    8. NEVER send unrelated fields with guessed/default values.

    9. In particular, do NOT send attendees unless the user explicitly
    asks to change the attendees.

    10. IMPORTANT:
        Updating "attendees" replaces the existing attendee list.
        Therefore, never include attendees in an update unless the user
        explicitly requests an attendee change.

    11. Supported update fields include:
        - summary
        - location
        - attendees
        - description
        - visibility
        - transparency
        - start__dateTime
        - end__dateTime
        - all_day
        - colorId
        - recurrence settings
        - reminders
        - send_notifications

    12. If the user changes only the title, update only summary.

    13. If the user changes only the location, update only location.

    14. If the user changes only the description, update only description.

    15. If the user changes only the start/end time, update only:
        start__dateTime
        end__dateTime

    16. If the user changes only the date, preserve the existing event
        time unless the user explicitly provides a new time.

    17. If the user changes only the time, preserve the existing event
        date unless the user explicitly provides a new date.

    18. For relative dates such as:
        today
        tomorrow
        next Monday
        this Friday

        resolve the date using the current date and user's local timezone.

    19. For relative times such as:
        10 AM
        2:30 PM
        14:00

        convert them to valid ISO-8601 date-time values.

    20. Preserve the user's local timezone when constructing event
        start/end values.

    21. Do NOT convert a local time to UTC manually if the Zapier tool
        accepts an ISO-8601 value containing the user's timezone offset.

    22. start__dateTime and end__dateTime must be valid ISO-8601
        date-time strings.

    23. Ensure end time is after start time.

    24. If the user asks to reschedule an event, update both start and
        end time when both are known.

    25. If the user gives a new duration instead of an explicit end time,
        calculate the end time from the new start time and duration.

    26. calendarid is required by the Zapier update tool. Resolve the
        appropriate calendar when necessary.

    27. eventid depends on calendarid. Resolve calendarid first, then
        resolve the event ID.

    28. The Zapier tool supports dynamic properties. If a field changes
        the dynamic property schema, resolve the dynamic property schema
        before making the final tool call. Never guess dynamic_properties.

    29. Always provide the required output_hint.

    30. After calling google_calendar_update_event:
        - Inspect the actual Zapier result.
        - Only report success if the tool confirms that the update
        succeeded.
        - If the tool returns an error, do not claim that the event was
        updated.
        - Explain the actual failure concisely.

    31. Do not claim an event was updated merely because the Zapier action
        was attempted.

    32. When successful, provide a concise confirmation containing the
        updated event information relevant to the user's request.

    33. If an event was found but no requested field could be safely
        determined, ask for clarification instead of making assumptions.


    EXAMPLES:

    User:
        "Rename Team Meeting to Project Meeting."

    Action:
        update_event

    Update:
        summary = "Project Meeting"


    User:
        "Move Team Meeting tomorrow from 10 AM to 2 PM."

    Action:
        update_event

    Update only:
        start__dateTime
        end__dateTime

    Preserve the existing duration unless the user specifies a new
    duration/end time.


    User:
        "Change the location of Team Meeting to Mumbai."

    Action:
        update_event

    Update only:
        location = "Mumbai"


    User:
        "Add Vinayak to the Team Meeting."

    Action:
        Do NOT blindly send attendees without knowing the existing
        attendee list, because the attendees field replaces the existing
        attendee list.

        Resolve the existing event/attendees first if the architecture
        supports it. Otherwise, ask for confirmation before replacing
        the attendee list.


    User:
        "Make the Team Meeting private."

    Action:
        update_event

    Update only:
        visibility = "private"


    User:
        "Change Team Meeting to free."

    Action:
        update_event

    Update only:
        transparency = "transparent"


    User:
        "Move the Team Meeting to 3 PM."

    Action:
        Preserve the event's existing date and duration.
        Change only the relevant start/end time values.

    ======================================
    GOOGLE CALENDAR — DELETE EVENT
    ======================================

    When the user asks to delete, cancel, remove, or erase a Google Calendar event:

    1. If the event ID is already available from a previous Google Calendar operation, use it directly.

    2. If the event ID is NOT available, first call google_calendar_find_events to locate the event.

    3. When searching for the event:
    - Use the user's specified date/time range whenever available.
    - Use search_term only when the user explicitly identifies the event by title or description.
    - Use attendee_email when the user identifies an attendee by email.
    - Resolve the user's calendar when calendarid is not explicitly available.

    4. If exactly one matching event is found:
    - Extract its event_id.
    - Extract its calendarid.
    - Call google_calendar_delete_event using those values.

    5. If multiple matching events are found:
    - DO NOT delete any event automatically.
    - Ask the user which event they want to delete.
    - Show enough identifying information such as title, date, start time, and attendee.

    6. If no matching event is found:
    - Do not call google_calendar_delete_event.
    - Tell the user that no matching event was found.

    7. google_calendar_delete_event requires:
    - calendarid
    - eventid
    - output_hint

    8. Never invent an event ID or calendar ID.

    9. Do not claim that an event was deleted unless google_calendar_delete_event returns a successful result.

    10. After successful deletion, respond concisely with the event title and scheduled date/time when available.

    Example:

    User:
    "Delete my Team Meeting tomorrow."

    Correct workflow:
    1. Find events for tomorrow with search_term="Team Meeting".
    2. If one event is found, obtain event_id and calendarid.
    3. Delete that exact event.
    4. Confirm successful deletion.

    If the user explicitly provides an event ID, do not perform an unnecessary search; use the provided event ID with the appropriate calendar.

    ===============================================================



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
