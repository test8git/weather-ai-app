from langgraph.prebuilt import create_react_agent

from services.llm_service import llm
from tools.weather_tool import get_weather
from tools.memory_tool import save_message, get_history


# Give the AI access to this tool/function
tools = [get_weather]

# An AI Agent
graph = create_react_agent(
    llm,
    tools
)

def run_agent(question, session_id):

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
        answer = "AI service temporarily unavailable. Please try again later."

    # SAVE AI MESSAGE
    save_message(session_id, "assistant", answer)

    return answer