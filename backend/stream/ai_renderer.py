from langchain_core.messages import AIMessage

from stream.context import StreamContext
from common.sse import sse_event, sse_step


class AIRenderer:

    async def render(self, chunk, ctx: StreamContext):

        events = []

        #
        # ToolRenderer already produced
        # the final answer.
        #
        if ctx.finished:
            return []

        #
        # LangGraph v1.2
        #
        # chunk is AIMessageChunk
        #

        if not hasattr(chunk, "content"):
            return events

        content = chunk.content

        #
        # Empty token
        #
        if not content:
            return events

        #
        # AIMessageChunk.content
        #
        # Sometimes:
        #
        # "Hello"
        #
        if isinstance(content, str):

            ctx.answer += content

            events.append(
                {
                    "type": "token",
                    "content": content,
                    "sse": sse_event(
                        "message",
                        content,
                    ),
                }
            )

            return events

        #
        # Gemini may return:
        #
        # [
        #     {"text":"Hello"}
        # ]
        #

        if isinstance(content, list):

            for item in content:

                if not isinstance(item, dict):
                    continue

                text = item.get("text")

                if not text:
                    continue

                ctx.answer += text

                events.append(
                    {
                        "type": "token",
                        "content": text,
                        "sse": sse_event(
                            "message",
                            text,
                        ),
                    }
                )

        return events


ai_renderer = AIRenderer()

# # # class AIRenderer:

# # #     async def render(self, message, ctx: StreamContext):

# # #         events = []

# # #         #
# # #         # Skip AI output after a tool has already produced the final response
# # #         #
# # #         if ctx.skip_remaining_ai:
# # #             ctx.skip_remaining_ai = False
# # #             return []

# # #         #
# # #         # Ignore intermediate AI messages that only contain tool calls
# # #         #
# # #         if isinstance(message, AIMessage):

# # #             if getattr(message, "tool_calls", None):
# # #                 return events

# # #         # No content
# # #         if not hasattr(message, "content"):
# # #             return events

# # #         content = message.content

# # #         #
# # #         # Gemini / OpenAI sometimes return:
# # #         #
# # #         # "Hello"
# # #         #
# # #         if isinstance(content, str):

# # #             clean_content = content

# # #             if clean_content:

# # #                 if clean_content != ctx.last_content:

# # #                     ctx.append(clean_content)

# # #                     events.append(
# # #                         {
# # #                             "type": "token",
# # #                             "content": clean_content,
# # #                             "sse": sse_event(
# # #                                 "message",
# # #                                 clean_content,
# # #                             ),
# # #                         }
# # #                     )

# # #             return events

# # #         #
# # #         # Gemini sometimes returns:
# # #         #
# # #         # [
# # #         #   {
# # #         #      "text":"Hello"
# # #         #   }
# # #         # ]
# # #         #
# # #         if isinstance(content, list):

# # #             for item in content:

# # #                 if not isinstance(item, dict):
# # #                     continue

# # #                 text = item.get("text", "")

# # #                 if not text:
# # #                     continue

# # #                 if text == ctx.last_content:
# # #                     continue

# # #                 ctx.append(text)

# # #                 events.append(
# # #                     {
# # #                         "type": "token",
# # #                         "content": text,
# # #                         "sse": sse_event(
# # #                             "message",
# # #                             text,
# # #                         ),
# # #                     }
# # #                 )

# # #         return events


# # # ai_renderer = AIRenderer()
