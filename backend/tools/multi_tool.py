from tavily import TavilyClient
from newsapi import NewsApiClient
import wikipedia
from langchain.tools import tool
import requests
from pathlib import Path
from dotenv import load_dotenv
import os


# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

newsapi = NewsApiClient(
    api_key=os.getenv("NEWS_API_KEY")
)

@tool(description="Get current weather for a city")
def get_weather(city: str):

    try:
        WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"

        response = requests.get(url, timeout=20)

        data = response.json()

        if response.status_code != 200:

            error_message = data.get("message", "Unknown error")

            return f"""
Unable to get weather for '{city}'.

Error:
{error_message}
"""
   

        return f"""
        City: {city}
        Temperature: {data['main']['temp']}°C
        Weather: {data['weather'][0]['description']}
        Humidity: {data['main']['humidity']}%
        """
    
    except requests.exceptions.Timeout:
        return "Weather API request timed out."

    except requests.exceptions.ConnectionError:
        return "Unable to connect to weather service."

    except KeyError as e:
        return f"Missing expected weather data: {str(e)}"

    except Exception as e:
        return f"Unexpected error: {str(e)}"



@tool(description="Calculate expression")
def calculate_expression(expression: str):
    return eval(expression)


@tool(description="Get current time")
def current_time(expression: str):
    from datetime import datetime
    return str(datetime.now())

@tool(description="Search the web for latest information")
def search_news(query: str) -> str:
    
    try:

        response = newsapi.get_everything(
            q=query,
            language="en",
            sort_by="relevancy",
            page_size=5
        )

        articles = response.get("articles", [])

        if not articles:
            return "No news found."

        output = []

        for article in articles:

            output.append(
                f"""
Title: {article.get('title')}

Description:
{article.get('description')}

URL:
{article.get('url')}
"""
            )

        return "\n\n".join(output)

    except Exception as e:

        return f"News API Error: {str(e)}"
        



@tool(description="Search latest news articles")
def search_web(query: str) -> str:
    
    try:

        response = tavily_client.search(
            query=query,
            topic="news",
            search_depth="advanced",
            max_results=5
        )

        output = []

        for r in response["results"]:

            output.append(
                f"""
                Title: {r['title']}
                Content: {r['content']}
                URL: {r['url']}
                """
            )

        return "\n\n".join(output)

    except Exception as e:

        return f"Search Error: {str(e)}"



@tool(description="Search Wikipedia and return summary")
def wikipedia_search(query: str) -> str:
    
    try:

        result = wikipedia.summary(
            query,
            sentences=3
        )

        return result

    except Exception as e:

        return f"Wikipedia Error: {str(e)}"


  
        