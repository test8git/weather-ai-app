import uuid
from pathlib import Path
import os
from langchain.tools import tool
from dotenv import load_dotenv
###from google import genai
from PIL import Image
import urllib.parse
from langchain_core.tools import tool
import random

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# # # @tool(description="Generate an image from text")
# # # def generate_image_using_gemini(prompt: str):

# # #     try:
# # #         geminiClient = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# # #         response = geminiClient.models.generate_content(
# # #             model="gemini-3.1-flash-image",
# # #             contents=[
# # #                 prompt
# # #             ]
# # #         )

# # #         if not response.parts:
# # #             return {
# # #                 "success": False,
# # #                 "type": "image",
# # #                 "message": "Image generation failed."
# # #             }

# # #         for part in response.parts:

# # #             if getattr(part, "inline_data", None):

# # #                 UPLOAD_DIR = "uploads"
# # #                 os.makedirs(UPLOAD_DIR, exist_ok=True)

# # #                 filename = os.path.join(
# # #                     UPLOAD_DIR,
# # #                     f"{uuid.uuid4()}.png"
# # #                 )

# # #                 image = part.as_image()
# # #                 image.save(filename)

# # #                 return {
# # #                     "success": True,
# # #                     "type": "image",
# # #                     "url": filename
# # #                 }

# # #         #
# # #         # No image found.
# # #         # Maybe the model returned text instead.
# # #         #

# # #         text = ""

# # #         for part in response.parts:

# # #             if getattr(part, "text", None):
# # #                 text += part.text

# # #         return {
# # #             "success": False,
# # #             "type": "image",
# # #             "message": text or "The model did not generate an image."
# # #         }

# # #     except Exception as ex:

# # #         return {
# # #             "success": False,
# # #             "type": "image",
# # #             "message": str(ex)
# # #         }
    

@tool(description="Generate an image from a text prompt")
def generate_image(prompt: str):

    """
    Generate an image using Pollinations AI.
    """

    try:
        
        seed = random.randint(1, 1000)


        encoded_prompt = urllib.parse.quote(prompt)

        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=512"
            f"&height=512"
            f"&model=flux"
            f"&seed={seed}"
        )

        return {
            "success": True,
            "type": "image",
            "image_url": image_url
        }

    except Exception as ex:

        return {
            "success": False,
            "type": "image",
            "message": str(ex)
        }