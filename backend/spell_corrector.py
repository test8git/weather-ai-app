# # # from dotenv import load_dotenv
# # # import os

# # # from google import genai
# # # import json


# # # load_dotenv()

# # # SPELL_PROMPT = f"""
# # # You are a spelling correction engine.

# # # Your ONLY job is to correct spelling mistakes.

# # # Rules:

# # # 1. Correct spelling mistakes only.
# # # 2. Never answer the user's question.
# # # 3. Never explain anything.
# # # 4. Never summarize.
# # # 5. Never translate.
# # # 6. Preserve the original meaning.
# # # 7. Preserve company names.
# # # 8. Preserve city names.
# # # 9. Preserve API names.
# # # 10. Preserve programming language names.
# # # 11. Preserve library names.
# # # 12. Preserve GitHub repository names whenever possible.
# # # 13. Preserve stock symbols.
# # # 14. Preserve numbers.
# # # 15. If the sentence is already correct,
# # # return it unchanged.

# # # 16. Return ONLY valid JSON.

# # # Format

# # # {
# # #     "original": "...",
# # #     "corrected": "...",
# # #     "changed": true
# # # }

# # # Examples

# # # Input

# # # Rosterent in Jaipur

# # # Output

# # # {
# # # "original":"Rosterent in Jaipur",
# # # "corrected":"Restaurant in Jaipur",
# # # "changed":true
# # # }

# # # Input

# # # Aple stock

# # # Output

# # # {
# # # "original":"Aple stock",
# # # "corrected":"Apple stock",
# # # "changed":true
# # # }

# # # Input

# # # Langgrahp tutorial

# # # Output

# # # {
# # # "original":"Langgrahp tutorial",
# # # "corrected":"LangGraph tutorial",
# # # "changed":true
# # # }

# # # Input

# # # What is Reliance stock today

# # # Output

# # # {
# # # "original":"What is Reliance stock today",
# # # "corrected":"What is Reliance stock today",
# # # "changed":false
# # # }
# # # """

# # # spell_client = genai.Client(
# # #     api_key=os.getenv("GEMINI_API_KEY")
# # # )


# # # def correct_question(question):

# # #     response = spell_client.models.generate_content(

# # #         model=os.getenv("GEMINI_AI_MODAL"),

# # #         contents=[
# # #             SPELL_PROMPT,
# # #             question
# # #         ]
# # #     )

# # #     text = response.text.strip()

# # #     try:
# # #         return json.loads(text)
# # #     except:

# # #         return {

# # #             "original": question,

# # #             "corrected": question,

# # #             "changed": False

# # #         }