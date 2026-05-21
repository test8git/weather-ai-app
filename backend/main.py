from fastapi import FastAPI
from typing import List, Dict, Any
from pydantic import BaseModel
from graph.weather_graph import graph
from graph.chat_graph import chat_graph
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
# Allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/weather")
def weather_ai(city: str):

    result = graph.invoke({
        "city": city
    })

    return result

class ChatRequest(BaseModel):
    city: str
    question: str
    forecast: List[Dict[str, Any]]

@app.post("/chat")
def chat_weather(data: ChatRequest):

    result = chat_graph.invoke({
        "city": data.city,
        "question": data.question,
        "forecast": data.forecast
    })

    return result    