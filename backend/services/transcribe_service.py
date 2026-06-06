import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import mimetypes

from dotenv import load_dotenv
import os

load_dotenv()

def transcribe_audio(audio_path):

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_AI_MODAL"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    mime_type, _ = mimetypes.guess_type(audio_path)

    if mime_type is None:
        mime_type = "audio/webm"

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": "Transcribe this audio exactly. Return only the transcript."
            },
            {
                "type": "media",
                "mime_type": mime_type,   # change if needed
                "data": audio_b64
            }
        ]
    )

    response = llm.invoke([message])

    return response.content