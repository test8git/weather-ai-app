from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_groq import ChatGroq

from dotenv import load_dotenv
import os

load_dotenv()

def get_llm(provider):

    provider = provider.lower()

    print(f"AI Modal = {provider}");

    # GEMINI
    if provider == "gemini":
        
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_AI_MODAL"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.2,
            streaming=True
        )

    # OPENAI
    elif provider == "openai":

        return ChatOpenAI(
            model=os.getenv("OPENAI_AI_MODAL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=1500,
            temperature=0.2,
            streaming=True
        )

    # CLAUDE
    elif provider == "claude":

        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_AI_MODAL"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=2000,
            temperature=0.2,
            streaming=True
        )

    # OPENROUTER
    elif provider == "openrouter":

        return ChatOpenAI(
            model=os.getenv("OPENROUTER_AI_MODAL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": os.getenv("FRONTEND_URL"),
                "X-Title": "AI App"
            },
            max_tokens=2000,
            temperature=0.2,
            streaming=True
        )

    # GROK (xAI)
    elif provider == "grok":

        return ChatOpenAI(
            model=os.getenv("XAI_GROK_AI_MODAL"),
            api_key=os.getenv("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
            temperature=0.2,
            streaming=True
        )

    # GROQ
    elif provider == "groq":

        return ChatGroq(
            model=os.getenv("GROQ_AI_MODAL"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2,
            streaming=True
        )

    else:
        raise Exception("Unsupported AI provider")