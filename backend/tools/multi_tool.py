from tavily import TavilyClient
from newsapi import NewsApiClient
import wikipedia
from langchain.tools import tool
import requests
from pathlib import Path
from dotenv import load_dotenv
import os
import re
import json
from urllib.parse import unquote
from tools.finance_resolver import resolve_symbol
import yfinance as yf
from yahooquery import search


# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

tavily_client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# newsapi = NewsApiClient(
#     api_key=os.getenv("NEWS_API_KEY")
# )

#tavily search
def tavily_search(query, max_results=5):
    try:

        response = tavily_client.search(
            query=query,
            topic="general",
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
            include_domains=[],
            exclude_domains=[]
        )

        output = []

        answer = response.get("answer", "")

        if answer:
            output.append(f"Answer:\n{answer}")

        for r in response.get("results", []):

            title = r.get("title", "")
            url = r.get("url", "")
            content = clean_text(r.get("content", ""))

            output.append(
                f"""
                Source: {url}
                Title: {title}
                Summary: {content}
                """
            )

        return "\n\n".join(output)

    except Exception as e:

        return f"Search Error: {str(e)}"


#function for clean text
def clean_text(text: str) -> str:

    if not text:
        return ""

    # Decode URL encoding
    text = unquote(text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()

#@tool(description="Get current weather for a city")
@tool(description="Get Current weather Feels like Wind Humidity Pressure Visibility Sunrise Sunset for a city")
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


@tool(description="Get current time")
def current_time(expression: str):
    from datetime import datetime
    return str(datetime.now())

def newsapi_search(query):

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": NEWS_API_KEY
    }

    r = requests.get(url, params=params, timeout=30)

    if r.status_code != 200:
        return []

    data = r.json()
    return data.get("articles", [])

def tavily_search_news(query):

    response = tavily_client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=True

    )

    return response

@tool(description="""
        Search latest news.
        Use for:
        - latest news
        - current events
        - sports
        - politics
        - business
        - technology
        - AI
        - current events
        """)
def search_news(query: str) -> str:
    
    try:
        
        news = newsapi_search(query)

        tavily_result = tavily_search_news(query)

        output = ""

        #
        # NewsAPI
        #

        # output += "========== NEWSAPI ==========\n\n"

        if news:

            for article in news:

                output += f"""
                        Title:
                        {article['title']}

                        Source:
                        {article['source']['name']}

                        Published:
                        {article['publishedAt']}

                        Description:
                        {article['description']}

                        URL:
                        {article['url']}

                        --------------------------------------

                        """

        #
        # Tavily
        #

        # output += "\n\n========== TAVILY ==========\n\n"

        if tavily_result.get("answer"):

            output += f"""
            Summary:
            {tavily_result['answer']}

            """

        for item in tavily_result.get("results", []):

            output += f"""
                Title:
                {item['title']}

                Content:
                {item['content']}

                URL:
                {item['url']}

                -------------------------------------

                """

        return output

    except Exception as e:

        return f"News API Error: {str(e)}"
        

@tool(description="Search the web")
def search_web(query: str) -> str:
    
    return tavily_search(query, 5)
    


@tool(description="Search Wikipedia and return summary")
def wikipedia_search(query: str) -> str:

    try:

        results = wikipedia.search(query)

        if not results:
            return ""

        page_title = results[0]

        return wikipedia.summary(
            page_title,
            sentences=6
        )

    except Exception:
        return ""


@tool(description="Search programming documentation, StackOverflow, GitHub, official docs.")
def search_programming(query: str):
    q = query.lower()
    search_query = ""

    if "c#" in q or ".net" in q:

        search_query = f"""
        site:learn.microsoft.com
        OR site:stackoverflow.com
        OR site:github.com

        {query}
        """

    elif "python" in q:

        search_query = f"""
        site:docs.python.org
        OR site:fastapi.tiangolo.com
        OR site:stackoverflow.com
        OR site:github.com

        {query}
        """

    elif "php" in q:

        search_query = f"""
        site:php.net
        OR site:stackoverflow.com
        OR site:github.com

        {query}
        """

    elif "react" in q:

        search_query = f"""
        site:react.dev
        OR site:stackoverflow.com
        OR site:github.com

        {query}
        """

    else:

        search_query = f"""
        site:stackoverflow.com
        OR site:github.com

        {query}
        """
    
    return tavily_search(search_query, 5)


@tool(description="""
        Use this tool whenever the user asks about:
        Stocks
        indexes
        cryptocurrencies
        ETFs
        commodities
        Share price
        Stock market
        NASDAQ
        NYSE
        NSE
        BSE
        Market cap
        Dividend
        PE ratio
        52 week high
        52 week low
        Trading volume
        
        Ticker symbols

        Examples:
        Apple stock
        Tesla stock
        Reliance share
        Microsoft stock
        TCS share price
        NVIDIA PE ratio
        """)
def search_finance(query: str) -> str:

    try:

        asset = resolve_symbol(query)

        if asset is None:

            return {
                "success":False,
                "message": f"Unable to identify '{query}'."
            }

        symbol = asset["symbol"]

        stock = yf.Ticker(symbol)

        info = stock.info

        return f"""
        Company:
        {info.get("longName")}

        Ticker:
        {symbol}

        Current Price:
        {info.get("currentPrice")}

        Previous Close:
        {info.get("previousClose")}

        Open:
        {info.get("open")}

        Day High:
        {info.get("dayHigh")}

        Day Low:
        {info.get("dayLow")}

        52 Week High:
        {info.get("fiftyTwoWeekHigh")}

        52 Week Low:
        {info.get("fiftyTwoWeekLow")}

        Market Cap:
        {info.get("marketCap")}

        PE Ratio:
        {info.get("trailingPE")}

        Dividend Yield:
        {info.get("dividendYield")}

        Volume:
        {info.get("volume")}
        """

    except Exception as e:

        return str(e)

  
        