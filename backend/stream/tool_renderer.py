import json
from langchain_core.messages import ToolMessage
from stream.context import StreamContext
from stream.progress import *

from services.html_builder import *

from common.sse import sse_event, sse_step

class ToolRenderer:

    async def render_event(self, event, ctx: StreamContext):

        output = event["data"].get("output")

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

        if tool_result.get("status") == "SUCCESS":

            #
            # send_email
            #

            if tool_result.get("action") == "send_email":

                ctx.skip_next_ai_message = True

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
        # ----------------------------
        # Unknown Tool
        # ----------------------------
        #

        return False, []


tool_renderer = ToolRenderer()

# # # class ToolRenderer:

# # #     async def render(self, message, ctx: StreamContext):

# # #         if not isinstance(message, ToolMessage):
# # #             return False, []

# # #         events = []

# # #         #
# # #         # Search progress completed
# # #         #
# # #         if ctx.progress.searching_started:

# # #             ctx.progress.searching_started = False

# # #             events.append(
# # #                 progress_manager.searching_completed_fun()
# # #             )
# # #         #
# # #         # Parse JSON
# # #         #
# # #         try:
# # #             tool_result = json.loads(message.content)

# # #         except Exception:
# # #             return False, []

# # #         #
# # #         # ----------------------------
# # #         # Calculator
# # #         # ----------------------------
# # #         #

# # #         if tool_result.get("type") == "calculator":

# # #             text = f"""
# # #                 Expression:
# # #                 {tool_result["expression"]}

# # #                 Answer:
# # #                 {tool_result["result"]}
# # #                 """

# # #             ctx.answer = text

# # #             events.append(
# # #                 {
# # #                     "type": "tool",
# # #                     "content": text,
# # #                     "sse": sse_event(
# # #                         "message",
# # #                         text,
# # #                     ),
# # #                 }
# # #             )

# # #             return True, events

# # #         #
# # #         # ----------------------------
# # #         # Image
# # #         # ----------------------------
# # #         #

# # #         if tool_result.get("type") == "image":

# # #             events.append(
# # #                 {
# # #                     "type": "image",
# # #                     "content": tool_result["image_url"],
# # #                     "sse": sse_event(
# # #                         "image",
# # #                         tool_result["image_url"],
# # #                     ),
# # #                 }
# # #             )

# # #             return True, events

# # #         #
# # #         # ----------------------------
# # #         # Github
# # #         # ----------------------------
# # #         #

# # #         if tool_result.get("type") == "github":

# # #             markdown = ""

# # #             for repo in tool_result["repositories"]:

# # #                 body = ""

# # #                 body += paragraph(repo["description"])

# # #                 body += bold(f"⭐ {repo['stars']}")

# # #                 body += line_break()

# # #                 body += hyperlink(
# # #                     "Open Repository",
# # #                     repo["url"],
# # #                 )

# # #                 markdown += card(
# # #                     repo["full_name"],
# # #                     body,
# # #                 )

# # #             ctx.answer = markdown

# # #             events.append(
# # #                 {
# # #                     "type": "tool",
# # #                     "content": markdown,
# # #                     "sse": sse_event(
# # #                         "message",
# # #                         markdown,
# # #                     ),
# # #                 }
# # #             )

# # #             return True, events

# # #         #
# # #         # ----------------------------
# # #         # Google Places
# # #         # ----------------------------
# # #         #

# # #         if tool_result.get("type") == "places":

# # #             items = []

# # #             for place in tool_result["places"]:

# # #                 if place.get("google_maps"):

# # #                     link = hyperlink(
# # #                         "Open Google Maps",
# # #                         place["google_maps"],
# # #                     )

# # #                 else:

# # #                     link = hyperlink(
# # #                         "Open Link",
# # #                         place.get("url", ""),
# # #                     )

# # #                 items.append(

# # #                     bold(place["name"])
# # #                     + line_break()
# # #                     + link

# # #                 )

# # #             markdown = heading(ctx.current_question)

# # #             markdown += ordered_list(items)

# # #             ctx.answer = markdown

# # #             events.append(
# # #                 {
# # #                     "type": "tool",
# # #                     "content": markdown,
# # #                     "sse": sse_event(
# # #                         "message",
# # #                         markdown,
# # #                     ),
# # #                 }
# # #             )

# # #             return True, events

# # #         #
# # #         # ----------------------------
# # #         # Zapier
# # #         # ----------------------------
# # #         #

# # #         if tool_result.get("status") == "SUCCESS":

# # #             #
# # #             # send_email
# # #             #

# # #             if tool_result.get("action") == "send_email":

# # #                 ctx.skip_next_ai_message = True

# # #                 events.append(
# # #                     {
# # #                         "type": "tool",
# # #                         "content": f"✅ Email sent successfully to {tool_result['recipient']}",
# # #                         "sse": sse_event(
# # #                             "message",
# # #                             f"✅ Email sent successfully to {tool_result['recipient']}",
# # #                             # ""
# # #                         ),
# # #                     }
# # #                 )

# # #                 return True, events

# # #         #
# # #         # ----------------------------
# # #         # Unknown Tool
# # #         # ----------------------------
# # #         #

# # #         return False, []


# # # tool_renderer = ToolRenderer()