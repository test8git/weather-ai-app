import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import mimetypes
from PIL import Image

from dotenv import load_dotenv
import os

load_dotenv()

def analyze_image(image_path: str, llm, prompt) -> str:

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    # llm = ChatGoogleGenerativeAI(
    #     model=os.getenv("GEMINI_AI_MODAL"),
    #     google_api_key=os.getenv("GEMINI_API_KEY"),
    # )

    mime_type, _ = mimetypes.guess_type(image_path)

    response = llm.invoke(
        [
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "Describe this image in detail."
                    },
                    {
                        "type": "image_url",
                        "image_url": f"data:{mime_type};base64,{image_data}"
                    }
                ]
            )
        ]
    )

    return response.content    