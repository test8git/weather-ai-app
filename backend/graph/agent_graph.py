from langgraph.prebuilt import create_react_agent

from services.llm_factory import get_llm
from tools.weather_tool import get_weather
from tools.memory_tool import save_message, get_history

import json

# Give the AI access to this tool/function
tools = [get_weather]

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

def sse_event(event_type, content):
    return f"{json.dumps({
        "type": event_type,
        "content": content
    })}\n\n"

def run_agent_stream(question, session_id, selected_model):

    # Create LLM Dynamically
    llm = get_llm(selected_model)

    # Create Graph Dynamically
    graph = create_react_agent(llm, tools)

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

        # STATUS EVENT
        yield sse_event("status", "🧠 Thinking...")

        for message, metadata in graph.stream(
            {
                "messages": [("user", full_prompt)]
            },
            stream_mode="messages"
        ):

            # TOOL STATUS
            node = metadata.get("langgraph_node", "")

            if node == "tools":

                yield sse_event(
                    "status",
                    "🌦 Calling Weather API..."
                )

            elif node == "agent":

                yield sse_event(
                    "status",
                    "✍ Generating response..."
                )

            # print("MESSAGE =>", message)
            # print("CONTENT =>", message.content)

            if hasattr(message, "content"):

                content = message.content

                # STRING CONTENT
                if isinstance(content, str) and content.strip():

                    content = message.content

                    answer += content

                    # print("STREAMING:", content)

                    # yield f"data: {content}\n\n"

                    yield sse_event("message", content)


                # LIST CONTENT (Gemini sometimes returns list)
                elif isinstance(content, list):

                    for item in content:

                        if isinstance(item, dict):

                            text = item.get("text", "")

                            if text:

                                answer += text

                                # print("STREAMING:", text)

                                # yield f"data: {text}\n\n"

                                yield sse_event("message", text)

        # DONE
        yield sse_event("status", "")

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_message = repr(e)

        print("****************")
        print(e)
        print("****************")
        print(error_message)
        print("****************")

        # error_message = f"Error: {str(e)}"

        answer += error_message

        # STREAM ERROR
        # for word in error_message.split():
        #     # print("STREAMING:", word)
            
        #     yield f"data: {word} \n\n"

        yield sse_event("error", error_message)

    save_message(session_id, "assistant", answer)
