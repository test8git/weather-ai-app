from langchain_core.messages import AIMessageChunk

from stream.context import StreamContext
from common.sse import sse_event


class AIRenderer:

    @staticmethod
    def extract_text(content):

        if not content:
            return ""

        # -----------------------------------------
        # Normal string
        # -----------------------------------------

        if isinstance(content, str):
            return content

        # -----------------------------------------
        # Gemini / structured content
        # -----------------------------------------

        if isinstance(content, list):

            parts = []

            for item in content:

                if isinstance(item, str):
                    parts.append(item)
                    continue

                if isinstance(item, dict):

                    text = item.get("text")

                    if isinstance(text, str):
                        parts.append(text)

            return "".join(parts)

        return ""

    async def render(self, chunk, ctx: StreamContext):

        events = []

        #
        # Do not process anything after
        # an actual final response.
        #

        if ctx.finished:
            return []

        #
        # Debug
        #

        # # # print(
        # # #     "=== AI STREAM EVENT ==="
        # # # )

        # # # print(
        # # #     "Chunk type:",
        # # #     type(chunk).__name__
        # # # )

        # # # print(
        # # #     "Content type:",
        # # #     type(getattr(chunk, "content", None)).__name__
        # # # )

        #
        # AIMessageChunk
        #

        if not hasattr(chunk, "content"):
            return []

        content = self.extract_text(
            chunk.content
        )

        if not content:
            return []

        #
        # Store accumulated answer
        #

        ctx.answer += content

        #
        # Create SSE token
        #

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


ai_renderer = AIRenderer()







# # # from langchain_core.messages import AIMessage

# # # from stream.context import StreamContext
# # # from common.sse import sse_event, sse_step


# # # class AIRenderer:

# # #     async def render(self, chunk, ctx: StreamContext):

# # #         events = []

# # #         #
# # #         # ToolRenderer already produced
# # #         # the final answer.
# # #         #
# # #         if ctx.finished:
# # #             return []

# # #         #
# # #         # LangGraph v1.2
# # #         #
# # #         # chunk is AIMessageChunk
# # #         #

# # #         if not hasattr(chunk, "content"):
# # #             return events

# # #         content = chunk.content

# # #         #
# # #         # Empty token
# # #         #
# # #         if not content:
# # #             return events

# # #         #
# # #         # AIMessageChunk.content
# # #         #
# # #         # Sometimes:
# # #         #
# # #         # "Hello"
# # #         #
# # #         if isinstance(content, str):

# # #             ctx.answer += content

# # #             events.append(
# # #                 {
# # #                     "type": "token",
# # #                     "content": content,
# # #                     "sse": sse_event(
# # #                         "message",
# # #                         content,
# # #                     ),
# # #                 }
# # #             )

# # #             return events

# # #         #
# # #         # Gemini may return:
# # #         #
# # #         # [
# # #         #     {"text":"Hello"}
# # #         # ]
# # #         #

# # #         if isinstance(content, list):

# # #             for item in content:

# # #                 if not isinstance(item, dict):
# # #                     continue

# # #                 text = item.get("text")

# # #                 if not text:
# # #                     continue

# # #                 ctx.answer += text

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
