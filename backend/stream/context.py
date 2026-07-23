from dataclasses import dataclass, field

from stream.progress import ProgressState


@dataclass
class StreamContext:

    answer: str = ""

    tool_name: str = ""

    last_content: str = ""

    current_question: str = ""

    result_generated: bool = False

    skip_remaining_ai: bool = False

    progress: ProgressState = field(default_factory=ProgressState)

    def append(self, text):

        self.answer += text

        self.last_content = text