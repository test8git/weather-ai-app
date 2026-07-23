from langchain_core.messages import AIMessage
from langchain_core.messages import ToolMessage

from stream.context import StreamContext
from stream.ai_renderer import ai_renderer
from stream.tool_renderer import tool_renderer
from stream.progress import *


class StreamRunner:

    def __init__(self):

        self.progress = ProgressState()

    async def process(self, event, ctx):

        events = []

        event_type = event.get("event", "")

        if ctx.finished and event["event"] != "on_chain_end":
            return []

        #
        # ----------------------------------------
        # CHAT MODEL START
        # ----------------------------------------
        #

        if event_type == "on_chat_model_start":

            if not ctx.progress.generating_started:

                ctx.progress.generating_started = True

                events.append(
                    progress_manager.generating_started_fun()
                )

            return events

        #
        # ----------------------------------------
        # CHAT MODEL STREAM
        # ----------------------------------------
        #

        if event_type == "on_chat_model_stream":

            chunk = event["data"]["chunk"]

            ai_events = await ai_renderer.render(
                chunk,
                ctx,
            )

            events.extend(ai_events)

            return events

        #
        # ----------------------------------------
        # TOOL START
        # ----------------------------------------
        #

        if event_type == "on_tool_start":

            tool_name = event.get("name", "")

            ctx.current_tool_name = tool_name

            if not ctx.progress.searching_started:

                ctx.progress.searching_started = True

                events.append(
                    progress_manager.searching_started_fun()
                )

            return events

        #
        # ----------------------------------------
        # TOOL END
        # ----------------------------------------
        #

        if event_type == "on_tool_end":

            if ctx.progress.searching_started:

                ctx.progress.searching_started = False

                events.append(
                    progress_manager.searching_completed_fun()
                )

            handled, tool_events = await tool_renderer.render_event(
                event,
                ctx,
            )

            if handled:

                events.extend(tool_events)

            return events

        #
        # ----------------------------------------
        # CHAIN END
        # ----------------------------------------
        #

        if event_type == "on_chain_end":

            if ctx.progress.generating_started:

                ctx.progress.generating_started = False

                events.append(
                    progress_manager.generating_completed_fun()
                )

            return events

        return events


stream_runner = StreamRunner()



# # # class StreamRunner:

# # #     def __init__(self):

# # #         self.progress = ProgressState()

# # #     async def process(self, message, metadata, ctx):

# # #         events = []

# # #         #
# # #         # ------------------------------------
# # #         # TOOL CALL STARTED
# # #         # ------------------------------------
# # #         #

# # #         if isinstance(message, AIMessage):

# # #             if getattr(message, "tool_calls", None):

# # #                 #
# # #                 # Remember tool name
# # #                 #

# # #                 if message.tool_calls:

# # #                     ctx.current_tool_name = message.tool_calls[0]["name"]

# # #                 #
# # #                 # Analysis finished
# # #                 #

# # #                 if not ctx.progress.analyzing_completed:

# # #                     ctx.progress.analyzing_completed = True

# # #                     events.append(
# # #                         progress_manager.analyzing_completed_fun()
# # #                     )

# # #                 #
# # #                 # Searching...
# # #                 #

# # #                 if not ctx.progress.searching_started:

# # #                     ctx.progress.searching_started = True

# # #                     events.append(

# # #                         progress_manager.searching_started_fun()

# # #                     )

# # #                 return events

# # #         #
# # #         # ------------------------------------
# # #         # GENERATING...
# # #         # ------------------------------------
# # #         #

# # #         node = metadata.get(

# # #             "langgraph_node",

# # #             "",

# # #         )

# # #         if (node == "agent" and not ctx.progress.generating_started):

# # #             ctx.progress.generating_started = True

# # #             events.append(
# # #                 progress_manager.generating_started_fun()
# # #             )

# # #         #
# # #         # ------------------------------------
# # #         # TOOL MESSAGE
# # #         # ------------------------------------
# # #         #

# # #         handled, tool_events = await tool_renderer.render(message, ctx, )

# # #         if handled:

# # #             ctx.result_generated = True
            
# # #             events.extend(tool_events)

# # #             return events

# # #         #
# # #         # ------------------------------------
# # #         # AI MESSAGE
# # #         # ------------------------------------
# # #         #

# # #         ai_events = await ai_renderer.render(

# # #             message,

# # #             ctx,

# # #         )

# # #         events.extend(ai_events)

# # #         return events


# # # stream_runner = StreamRunner()