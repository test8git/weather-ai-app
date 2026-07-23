import requests
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime, timezone

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ZAPIER_WEBHOOK = os.getenv("ZAPIER_WEBHOOK")


def send_to_zapier(
    question: str,
    answer: str,
    model: str,
    session_id:str,
    user_email:str
):
    """
    Send chat details to Zapier.
    """

    if not ZAPIER_WEBHOOK:
        print("Zapier webhook not configured.")
        return

    current_datetime = datetime.now(timezone.utc).isoformat()

    payload = {
        "question": question,
        "answer": answer,
        "model": model,
        "user": session_id,
        "user_email":user_email,
        "created_at": current_datetime
    }

    try:

        response = requests.post(
            ZAPIER_WEBHOOK,
            json=payload,
            timeout=10
        )

        # print("Zapier:", response.status_code)

    except Exception as e:

        print("Zapier Error:", e)