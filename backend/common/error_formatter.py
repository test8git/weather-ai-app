import re
import json

def format_ai_error(err):
    text = str(err)

    print("ERROR FORMATTER : ")
    print(text)

    if "Error code: 402" in text:
        return "AI Model Credits Required"

    if "Error code: 429" in text:
        return "Rate Limit Exceeded"

    if "Error code: 401" in text:
        return "Invalid API Key"

    return "Unexpected Error"