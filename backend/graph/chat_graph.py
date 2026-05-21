from typing import TypedDict
from langgraph.graph import StateGraph, END

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from pathlib import Path
from dotenv import load_dotenv
from services.ai_service import llm

import requests
import os

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class ChatState(TypedDict):
    city: str
    question: str
    forecast: list
    weather: str
    answer: str


# Node 1
def get_weather(state: ChatState):

    city = state["city"]

    # WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

    # url = (
    #     f"https://api.openweathermap.org/data/2.5/weather"
    #     f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
    # )

    # data = requests.get(url).json()

    # Text for AI
    forecast_text = ""

    for item in state["forecast"]:

        forecast_text += (
            f"Date: {item['date']}\n"
            f"Temperature: {item['temp']}°C\n"
            f"Condition: {item['condition']}\n\n"
        )

    weather = f"""
    City: {city}
    forecast: {forecast_text}
    """

    return {
        "weather": weather
    }

# Node 2
def ask_ai(state: ChatState):

    prompt = f"""
    Weather Data:

    {state['weather']}

    User Question:
    {state['question']}

    Answer like a helpful weather assistant.
    Keep answer short.
    """

    answer = ""

    try:

        response = llm.invoke([
            HumanMessage(content=prompt)
        ])
        answer = response.content
    except Exception as e:

        print("Gemini Error:", e)

        answer = """
AI service temporarily unavailable.

Please try again later.
"""


    return {
        "answer": answer
    }

builder = StateGraph(ChatState)

builder.add_node("get_weather", get_weather)
builder.add_node("ask_ai", ask_ai)

builder.set_entry_point("get_weather")

builder.add_edge("get_weather", "ask_ai")
builder.add_edge("ask_ai", END)

chat_graph = builder.compile()        
