from typing import TypedDict, List
from langgraph.graph import StateGraph, END

import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from pathlib import Path
from dotenv import load_dotenv
from services.ai_service import llm

import os


# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# print("KEY:", os.getenv("GEMINI_API_KEY"))

# Graph State
class WeatherState(TypedDict):

    city: str
    weather: str
    current_temp: str
    current_condition: str
    current_icon: str
    advice: str
    forecast: List
    chart_data: List


# Node 1
def get_weather(state: WeatherState):

    city = state["city"]

    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

    weather_url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
    )

    forecast_response = requests.get(weather_url).json()

    current_weather = forecast_response["list"][0]
    current_temp = ""
    current_condition = ""
    current_icon = ""

    # Weather API failed
    if "list" not in forecast_response:

        return {
            "city": city,
            "weather": f"Forecast not available for {city}",
            "current_temp": current_temp,
            "current_condition": current_condition,
            "current_icon": current_icon,
            "forecast": [],
            "chart_data":[]
        }

    forecast_data = []
    chart_data = []

    # First 5 forecast items
    for item in forecast_response["list"][:8]:

        forecast_data.append({

            "date": item["dt_txt"],
            "temp": item["main"]["temp"],
            "condition": item["weather"][0]["description"],
            "icon": item["weather"][0]["icon"]
        })

        chart_data.append({
            "time": item["dt_txt"],   #  item["dt_txt"][11:16]    HH:MM
            "temp": item["main"]["temp"]
        })

    current_weather = forecast_response["list"][0]
    current_temp = current_weather["main"]["temp"]
    current_condition = current_weather["weather"][0]["description"]
    current_icon = current_weather["weather"][0]["icon"]

    # Text for AI
    forecast_text = ""

    for item in forecast_data:

        forecast_text += (
            f"Date: {item['date']}\n"
            f"Temperature: {item['temp']}°C\n"
            f"Condition: {item['condition']}\n\n"
        )

    return {
        "city": city,
        "weather": forecast_text,
        "current_temp": current_temp,
        "current_condition": current_condition,
        "current_icon": current_icon,
        "forecast": forecast_data,
        "chart_data": chart_data
    }


# Node 2
def generate_advice(state: WeatherState):

    prompt = f"""
    Weather forecast:

    {state['weather']}

    Give short and useful weather advice.
    """

    try:

        response = llm.invoke([
            HumanMessage(content=prompt)
        ])

        advice = response.content

        # current_temp = float(state['current_temp'])

        # if current_temp > 35:
        #     advice = "Very hot weather. Stay hydrated."
        # elif current_temp < 15:
        #     advice = "Cold weather. Wear warm clothes."
        # else:
        #     advice = "Weather is Pleasant."

    except Exception as e:

        print("Gemini Error:", e)

        advice = """
AI service unavailable right now.
    Basic Advice:
- Drink plenty of water
- Avoid direct sunlight
- Wear light clothes
- Stay indoors during afternoon
"""


    return {
        "advice": advice
    }


# Build graph
builder = StateGraph(WeatherState)

builder.add_node("get_weather", get_weather)
builder.add_node("generate_advice", generate_advice)

builder.set_entry_point("get_weather")

builder.add_edge("get_weather", "generate_advice")
builder.add_edge("generate_advice", END)

graph = builder.compile()