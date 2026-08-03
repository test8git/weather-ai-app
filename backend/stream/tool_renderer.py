import json
from langchain_core.messages import ToolMessage
from stream.context import StreamContext
from stream.progress import *

from services.html_builder import *

from common.sse import sse_event, sse_step

class ToolRenderer:

    @staticmethod
    def normalize_tool_result(result):

        #
        # ToolMessage
        #
        if isinstance(result, ToolMessage):
            result = result.content

        #
        # MCP returns a list
        #
        if isinstance(result, list):

            if not result:
                return None

            result = result[0]

        #
        # MCP item
        #
        if isinstance(result, dict):

            #
            # {
            #   "type":"text",
            #   "text":"{...json...}"
            # }
            #
            if "text" in result:

                text = result["text"]

                try:
                    return json.loads(text)

                except Exception:
                    return {"text": text}

            return result

        #
        # plain string
        #
        if isinstance(result, str):

            try:
                return json.loads(result)

            except Exception:
                return {"text": result}

        return None

    async def render_event(self, event, ctx: StreamContext):

        output = self.normalize_tool_result(event["data"].get("output"))

        if output is None:
            return False, []

        events = []

        #
        # Search progress completed
        #
        if ctx.progress.searching_started:

            ctx.progress.searching_started = False

            events.append(
                progress_manager.searching_completed_fun()
            )
        
        #
        # LangGraph may return ToolMessage
        #

        if isinstance(output, ToolMessage):
            output = output.content

        #
        # Parse JSON if needed
        #

        if isinstance(output, str):
            try:
                tool_result = json.loads(output)
            except Exception:
                return False, []

        else:
            tool_result = output

        #
        # ----------------------------
        # Calculator
        # ----------------------------
        #

        if tool_result.get("type") == "calculator":

            text = f"""
                Expression:
                {tool_result["expression"]}

                Answer:
                {tool_result["result"]}
                """

            ctx.answer = text

            events.append(
                {
                    "type": "tool",
                    "content": text,
                    "sse": sse_event(
                        "message",
                        text,
                    ),
                }
            )

            return True, events

        #
        # ----------------------------
        # Image
        # ----------------------------
        #

        if tool_result.get("type") == "image":

            events.append(
                {
                    "type": "image",
                    "content": tool_result["image_url"],
                    "sse": sse_event(
                        "image",
                        tool_result["image_url"],
                    ),
                }
            )

            return True, events

        #
        # ----------------------------
        # Github
        # ----------------------------
        #

        if tool_result.get("type") == "github":

            markdown = ""

            for repo in tool_result["repositories"]:

                body = ""

                body += paragraph(repo["description"])

                body += bold(f"⭐ {repo['stars']}")

                body += line_break()

                body += hyperlink(
                    "Open Repository",
                    repo["url"],
                )

                markdown += card(
                    repo["full_name"],
                    body,
                )

            ctx.answer = markdown

            events.append(
                {
                    "type": "tool",
                    "content": markdown,
                    "sse": sse_event(
                        "message",
                        markdown,
                    ),
                }
            )

            return True, events

        #
        # ----------------------------
        # Google Places
        # ----------------------------
        #

        if tool_result.get("type") == "places":

            items = []

            for place in tool_result["places"]:

                if place.get("google_maps"):

                    link = hyperlink(
                        "Open Google Maps",
                        place["google_maps"],
                    )

                else:

                    link = hyperlink(
                        "Open Link",
                        place.get("url", ""),
                    )

                items.append(

                    bold(place["name"])
                    + line_break()
                    + link

                )

            markdown = heading(ctx.current_question)

            markdown += ordered_list(items)

            ctx.answer = markdown

            events.append(
                {
                    "type": "tool",
                    "content": markdown,
                    "sse": sse_event(
                        "message",
                        markdown,
                    ),
                }
            )

            return True, events

        #
        # ----------------------------
        # Zapier
        # ----------------------------
        #

        #
        # ----------------------------
        # Zapier Follow-up Question
        # ----------------------------
        #

        if "followUpQuestion" in tool_result:

            question = tool_result["followUpQuestion"]

            ctx.answer = question

            ctx.finished = True

            events.append(
                {
                    "type": "tool",
                    "content": question,
                    "sse": sse_event(
                        "message",
                        question,
                    ),
                }
            )

            return True, events

        if tool_result.get("status") == "SUCCESS":

            #
            # send_email
            #

            if tool_result.get("action") == "send_email":

                ctx.finished = True

                events.append(
                    {
                        "type": "tool",
                        "content": f"✅ Email sent successfully to {tool_result['recipient']}",
                        "sse": sse_event(
                            "message",
                            f"✅ Email sent successfully to {tool_result['recipient']}",
                            # ""
                        ),
                    }
                )

                return True, events

            #
            # read_email
            #

            if tool_result.get("action") == "read_email":

                ctx.finished = True

                data = tool_result.get("data", {})

                # # # details = (
                # # #     data.get("results", {})
                # # #         .get("details", [])
                # # # )

                details = data.get("results", [])

                #
                # No emails found
                #

                if not details:

                    text = "No matching emails were found."

                    events.append(
                        {
                            "type": "tool",
                            "content": text,
                            "sse": sse_event(
                                "message",
                                text,
                            ),
                        }
                    )

                    return True, events

                #
                # Build markdown
                #

                markdown = "# Matching Emails\n\n"

                for email in details:

                    # # # markdown += (
                    # # #     f"## {email.get('subject','(No Subject)')}\n\n"
                    # # #     f"**From:** {email.get('from','')}\n\n"
                    # # #     f"**Date:** {email.get('date','')}\n\n"
                    # # #     f"{email.get('snippet','')}\n\n"
                    # # #     "---\n\n"
                    # # # )

                    from_info = email.get("from", {})

                    markdown += (
                        f"## {email.get('subject','(No Subject)')}\n\n"
                        f"**From:** {from_info.get('name','')} "
                        f"<{from_info.get('email','')}>\n\n"
                        f"**Date:** {email.get('date','')}\n\n"
                        f"{email.get('body_plain','')[:500]}\n\n"
                        "---\n\n"
                    )

                ctx.answer = markdown

                events.append(
                    {
                        "type": "tool",
                        "content": markdown,
                        "sse": sse_event(
                            "message",
                            markdown,
                        ),
                    }
                )

                return True, events    

        #
        # ----------------------------
        # Unknown Tool
        # ----------------------------
        #

        return False, []


tool_renderer = ToolRenderer()
