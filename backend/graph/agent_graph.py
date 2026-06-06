from langgraph.prebuilt import create_react_agent

import base64
import mimetypes
from PIL import Image
from langchain_core.messages import HumanMessage
from services.llm_factory import get_llm
from tools.multi_tool import search_web, get_weather, calculate_expression, current_time, search_news, wikipedia_search
from tools.memory_tool import save_message, get_history
from tools.file_tool import read_file_content
from services.transcribe_service import transcribe_audio

import json

# Give the AI access to this tool/function
tools = [search_web, get_weather, calculate_expression, current_time, search_news, wikipedia_search]

def sse_event(event_type, content):
    return f"{json.dumps({
        "type": event_type,
        "content": content
    })}\n\n"

def sse_step(step, status, icon):

    data = {
        "type": "step",
        "step": step,
        "status": status,
        "icon": icon
    }

    return f"{json.dumps(data)}\n\n"

def should_use_wikipedia(question):

    q = question.lower().strip()

    return (
        q.startswith("who is")
        or q.startswith("what is")
        or q.startswith("where is")
        or q.startswith("when was")
    )

def should_search(question):

    SEARCH_KEYWORDS = [
        "today",
        "latest",
        "current",
        "recent",
        "news",
        "cricket",
        "match",
        "champion",
        "final",
        "live",
        "score",
        "winner",
        "result",
        "weather",
        "sports",
        "ipl",
        "stock",
        "price",
        "bitcoin",
        "election"
    ]

    q = question.lower()

    return any(keyword in q for keyword in SEARCH_KEYWORDS)


def run_agent_stream(question, session_id, selected_model, file_path=None):

    yield sse_step(
        "Thinking...",
        "running",
        "🧠"
    )

    # Create LLM Dynamically
    llm = get_llm(selected_model)


    system_prompt = """

You are a professional AI assistant.

IMPORTANT BEHAVIOR RULES:

- Respond directly with the final answer.
- NEVER explain internal reasoning.
- NEVER narrate actions.
- NEVER mention tools.
- NEVER say:
    - "I will use..."
    - "Let me check..."
    - "Searching..."
    - "Using tool..."
    - "I need to search..."

TOOL USAGE RULES:

- Use tools whenever external or real-time information is required.
- Use weather tool for weather-related questions.
- Use search_news for:
    - news
    - sports
    - current events
    - recent information
    - today's updates

- Use calculator only for calculations.

- Do NOT refuse valid requests when a tool can answer them.
- If a tool is available, use it silently and provide the final answer only.

Always provide clean, concise, user-friendly responses.

"""

    # SAVE USER MESSAGE
    save_message(session_id, "user", question)

    answer = ""

    # GET OLD HISTORY
    history = get_history(session_id)

    file_data = read_file_content(file_path)

    file_prompt = ""

    if file_data["type"] == "image":
        try:
            yield sse_step(
                "Thinking...",
                "completed",
                "✔️"
            )

            yield sse_step(
                "Analyzing image...",
                "running",
                "🖼️"
            )
            with open(file_data["content"], "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            mime_type, _ = mimetypes.guess_type(file_data["content"])

            response = llm.invoke(
                [
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": question
                            },
                            {
                                "type": "image_url",
                                "image_url": f"data:{mime_type};base64,{image_data}"
                            }
                        ]
                    )
                ]
            )

            answer+=response.content

            yield sse_step(
                "Analyzing image...",
                "completed",
                "✔️"
            )

            yield sse_event(
                "message",
                response.content
            )

            save_message(session_id, "assistant", answer)

            return

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = repr(e)

            answer += error_message

            yield sse_event("error", error_message)

    else:

        fileContent = ""

        # Audio file
        if file_data["type"] == "audio":
            transcript = transcribe_audio(file_data["content"])
            file_data["content"] = transcript

        if file_data["content"]:
            file_prompt = f"""
            IMPORTANT:

            If the file contains an instruction, prompt, question,
            essay topic, coding task, or assignment,
            perform the task.

            If the user asks to explain, summarize, analyze,
            review, or extract information,
            then analyze the file.

            Respond appropriately.
            """

            fileContent = f"""
                Uploaded File:
                {file_data["content"]}
                """

        # COMBINE HISTORY + NEW QUESTION
        full_prompt = f"""
        Conversation History:
        {history}

        User Question:
        {question}

        {fileContent}

        {file_prompt}
        """

        try:        

            yield sse_step(
                "Thinking...",
                "completed",
                "✔️"
            )

            # CHECK FIRST
            if should_use_wikipedia(question):

                print("Wiki Search")

                yield sse_step(
                    "Searching web...",
                    "running",
                    "🌐"
                )

                search_result = wikipedia_search.invoke(question)

                yield sse_step(
                    "Searching web...",
                    "completed",
                    "✔️"
                )

                formatted = llm.invoke(
                    f"""
                    Question:
                    {question}

                    {fileContent}

                    Search Result:
                    {search_result}

                    Answer using both the uploaded file
                    and the search result if relevant.
                    """
                )

                answer+=formatted.content

                yield sse_event(
                    "message",
                    formatted.content
                )
                
                save_message(session_id, "assistant", answer)

                return

            # CHECK FIRST
            # if 1==2:
            if should_search(question):

                print("Search Web")

                yield sse_step(
                    "Searching web...",
                    "running",
                    "🌐"
                )

                search_result = search_web.invoke(question)

                yield sse_step(
                    "Searching web...",
                    "completed",
                    "✔️"
                )

                formatted = llm.invoke(
                    f"""
                    Question:
                    {question}

                    {fileContent}

                    Search Result:
                    {search_result}

                    Answer using both the uploaded file
                    and the search result if relevant.
                    """
                )

                answer+=formatted.content

                yield sse_event(
                    "message",
                    formatted.content
                )
                
                save_message(session_id, "assistant", answer)

                return

            # Create Graph Dynamically
            graph = create_react_agent(llm, tools, prompt=system_prompt)            

            # STATUS EVENT
            yield sse_step(
                "Analyzing your request...",
                "running",
                "🔍"
            )

            isAnalyzingCompleted = False
            isSearchingWeb = 0
            isGeneratingStarted = False

            for message, metadata in graph.stream(
                {
                    "messages": [("user", full_prompt)]
                },
                stream_mode="messages"
            ):
                if not isAnalyzingCompleted:
                    yield sse_step(
                        "Analyzing your request...",
                        "completed",
                        "✔️"
                    )
                    isAnalyzingCompleted = True

                # TOOL STATUS
                node = metadata.get("langgraph_node", "")

                # DETECT TOOL
                if hasattr(message, "tool_calls"):

                    # TOOL STARTED
                    if (isSearchingWeb==0):                    
                        yield sse_step(
                            "Searching web...",
                            "running",
                            "🔍"
                        )
                        isSearchingWeb = 1

                    for tool_call in message.tool_calls:

                        tool_name = tool_call.get("name", "")

                        print("TOOL =", tool_name)

                        #region (Old code)

                        # if tool_name == "get_weather":

                        #     yield sse_step(
                        #         "Searching web...",
                        #         "running",
                        #         "🌐"
                        #     )
                        # elif tool_name == "calculate_expression":

                        #     yield sse_step(
                        #         "Searching web...",
                        #         "running",
                        #         "🌐"
                        #     )
                        # elif tool_name == "current_time":

                        #     yield sse_step(
                        #         "Searching web...",
                        #         "running",
                        #         "🌐"
                        #     )
                        # elif tool_name == "search_web":

                        #     yield sse_step(
                        #         "Searching web...",
                        #         "running",
                        #         "🌐"
                        #     )
                        # elif tool_name == "wikipedia_search":

                        #     yield sse_step(
                        #         "Searching web...",
                        #         "running",
                        #         "🌐"
                        #     )
                        # elif tool_name == "search_news":

                        #     yield sse_step(
                        #         "Searching web...",
                        #         "running",
                        #         "🌐"
                        #     )

                        # endregion
                

                if node == "agent" and not isGeneratingStarted:
                    # TOOL COMPLETED → BACK TO AGENT
                    
                    yield sse_step(
                        "Generating response...",
                        "running",
                        "✍️"
                    )
                    isGeneratingStarted = True

                if hasattr(message, "content"):
                    if (isSearchingWeb==1):
                        yield sse_step(
                            "Searching web...",
                            "completed",
                            "✔️"
                        )
                        isSearchingWeb = 2

                    content = message.content

                    # STRING CONTENT
                    # if isinstance(content, str) and content.strip():
                    if isinstance(content, str):

                        content = message.content

                        # clean_content = content.strip()
                        clean_content = content

                        if clean_content:

                            answer += clean_content

                            yield sse_event("message", clean_content)


                    # LIST CONTENT (Gemini sometimes returns list)
                    elif isinstance(content, list):

                        for item in content:

                            if isinstance(item, dict):

                                text = item.get("text", "")

                                # clean_content = text.strip()
                                clean_content = text

                                if clean_content:

                                    answer += clean_content

                                    yield sse_event("message", clean_content)
                            

            # DONE
            # yield sse_event("status", "")

        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = repr(e)

            answer += error_message

            yield sse_event("error", error_message)

        save_message(session_id, "assistant", answer)

        yield sse_step(
            "Generating response...",
            "completed",
            "✔️"
        )


    

    return answer

