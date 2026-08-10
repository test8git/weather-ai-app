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
