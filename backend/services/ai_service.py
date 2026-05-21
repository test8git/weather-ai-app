from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model=os.getenv("AI_MODAL"),
    google_api_key=os.getenv("GEMINI_API_KEY")
)