from dataclasses import dataclass
from common.sse import sse_step


@dataclass
class ProgressState:
    """
    Maintains streaming progress state.
    """

    thinking_started: bool = False
    thinking_completed: bool = False

    analyzing_started: bool = False
    analyzing_completed: bool = False

    searching_started: bool = False
    searching_completed: bool = False

    generating_started: bool = False
    generating_completed: bool = False


class ProgressManager:

    #
    # Thinking
    #

    @staticmethod
    def thinking_started_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Thinking...",
                "running",
                "🧠",
            ),
        }

    @staticmethod
    def thinking_completed_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Thinking...",
                "completed",
                "✔️",
            ),
        }

    #
    # Analyzing
    #

    @staticmethod
    def analyzing_started_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Analyzing your request...",
                "running",
                "🔍",
            ),
        }

    @staticmethod
    def analyzing_completed_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Analyzing your request...",
                "completed",
                "✔️",
            ),
        }

    #
    # Searching
    #

    @staticmethod
    def searching_started_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Searching...",
                "running",
                "🌐",
            ),
        }

    @staticmethod
    def searching_completed_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Searching...",
                "completed",
                "✔️",
            ),
        }

    #
    # Generating
    #

    @staticmethod
    def generating_started_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Generating response...",
                "running",
                "✍️",
            ),
        }

    @staticmethod
    def generating_completed_fun():

        return {
            "type": "step",
            "sse": sse_step(
                "Generating response...",
                "completed",
                "✔️",
            ),
        }


progress_manager = ProgressManager()