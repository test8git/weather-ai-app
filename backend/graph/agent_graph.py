from langgraph.prebuilt import create_react_agent

from services.llm_factory import get_llm
from tools.multi_tool import get_weather, calculate_expression, current_time, search_web, wikipedia_search, search_news
from tools.memory_tool import save_message, get_history

import json

# Give the AI access to this tool/function
tools = [get_weather, calculate_expression, current_time, search_web, wikipedia_search, search_news]

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

def run_agent_stream(question, session_id, selected_model):

    # Create LLM Dynamically
    llm = get_llm(selected_model)

    # Create Graph Dynamically
    graph = create_react_agent(llm, tools)
    # graph = create_react_agent(llm, [])

    # SAVE USER MESSAGE
    save_message(session_id, "user", question)

    answer = ""

    # GET OLD HISTORY
    history = get_history(session_id)

    # COMBINE HISTORY + NEW QUESTION
    full_prompt = f"""
    Conversation History:
    {history}

    User Question:
    {question}
    """

    try:

        # yield sse_event("status", "🧠 Thinking...")
        # yield sse_step(
        #     "🧠 Thinking...",
        #     "running"
        # )



        # STATUS EVENT
        yield sse_step(
            "Analyzing your request...",
            "running",
            "🔍"
        )

        isAnalyzingCompleted = False
        isSearchingWeb = 0

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

            # print("META")
            # print(metadata)
            # print("MESSAGE")
            # print(message)
            # print("Node = " + node)

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

                    # print("TOOL =", tool_name)

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
            

            if node == "agent":
                # TOOL COMPLETED → BACK TO AGENT
                
                yield sse_step(
                    "Generating response...",
                    "running",
                    "✍️"
                )

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
                if isinstance(content, str) and content.strip():

                    content = message.content

                    clean_content = content.strip()

                    if clean_content:

                        answer += clean_content+" "

                        yield sse_event("message", clean_content+" ")


                # LIST CONTENT (Gemini sometimes returns list)
                elif isinstance(content, list):

                    for item in content:

                        if isinstance(item, dict):

                            text = item.get("text", "")

                            clean_content = text.strip()

                            if clean_content:

                                answer += clean_content+" "

                                yield sse_event("message", clean_content+" ")
                        

        # DONE
        # yield sse_event("status", "")

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_message = repr(e)

        # print("****************")
        # print(e)
        # print("****************")
        # print(error_message)
        # print("****************")

        # error_message = f"Error: {str(e)}"

        answer += error_message

        # STREAM ERROR
        # for word in error_message.split():
        #     # print("STREAMING:", word)
            
        #     yield f"data: {word} \n\n"

        yield sse_event("error", error_message)

    save_message(session_id, "assistant", answer)

    yield sse_step(
        "Generating response...",
        "completed",
        "✔️"
    )


def run_agent(question, session_id, selected_model):

    # Create LLM Dynamically
    llm = get_llm(selected_model)

    # Create Graph Dynamically
    graph = create_react_agent(llm, tools)

    # SAVE USER MESSAGE
    save_message(session_id, "user", question)

    # GET OLD HISTORY
    history = get_history(session_id)

    # COMBINE HISTORY + NEW QUESTION
    full_prompt = f"""
    Conversation History:
    {history}

    User Question:
    {question}
    """

    # AGENT CALL
    try:
        result = graph.invoke({
            "messages": [
                ("user", full_prompt)
            ]
        })

        answer = result["messages"][-1].content
    except Exception as e:
        print(e)
        answer = "AI service temporarily unavailable. Please try again later. Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum."

    # SAVE AI MESSAGE
    save_message(session_id, "assistant", answer)

    return answer

