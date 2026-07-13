import os
import uuid
from database import init_db
from fastapi import FastAPI, UploadFile, File, Form
import tempfile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

import json
from threading import Thread
from pydantic import BaseModel
from graph.agent_graph import run_agent_stream
from services.transcribe_service import transcribe_audio
from tools.zapier_tool import send_to_zapier

import asyncio

app = FastAPI()

# initialize DB
init_db()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # # def extract_text(chunk: str) -> str:
# # #     try:
# # #         data = json.loads(chunk)

# # #         # {"type":"message","content":"Hello"}
# # #         if isinstance(data, dict):
# # #             return data.get("content", "")

# # #         return ""

# # #     except json.JSONDecodeError:
# # #         # Chunk is plain text
# # #         return chunk

# # #     except Exception as e:
# # #         print("extract_text:", e)
# # #         return ""


def extract_text(chunk):

    try:

        data = json.loads(chunk)

        if data["type"] == "message":
            return data["content"]

        elif data["type"] == "image":
            return "[Generated Image]"

        elif data["type"] == "chart":
            return "[Chart]"

        elif data["type"] == "code":
            return "[Code]"

        elif data["type"] == "places":
            return "[content]"

        return "[content]"

    except Exception:
        return "[content]"


class ChatRequest(BaseModel):
    question: str
    session_id: str
    selected_model: str


@app.get("/")
def root():
    return {
        "status": "General AI Assistant Backend Running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):

    tmp_file = tempfile.NamedTemporaryFile(delete=False)

    try:

        tmp_file.write(await audio.read())
        tmp_file.close()

        transcript = transcribe_audio(tmp_file.name)

        print(tmp_file.name)

        return {
            "transcript": transcript
        }

    finally:

        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)




@app.post("/chat")
async def chat(
    question: str = Form(...),
    session_id: str = Form(...),
    selected_model: str = Form(...),
    file: UploadFile | None = File(None)
):

    content_type = None
    file_path = None
    UPLOAD_DIR = "uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    try:
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)

            if os.path.isfile(file_path):
                os.remove(file_path)

    except Exception as e:
        pass


    if file:
        file_path = os.path.join(UPLOAD_DIR,  str(uuid.uuid4()) + "_" + file.filename)
        content_type = file.content_type

        with open(file_path, "wb") as f:
            f.write(await file.read())

    async def generate():
        answer = ""

        for chunk in run_agent_stream(
            question,
            session_id,
            selected_model,
            file_path,
            content_type
        ):

            answer += extract_text(chunk)

            # SSE FORMAT
            yield f"data: {chunk}\n\n"

            await asyncio.sleep(0.02)
        
        # print("ANSWER : ")
        # print(answer)

        responseToZaiper = answer
        # if len(responseToZaiper) > 300:
        #     responseToZaiper = responseToZaiper[:300] + "\n\n...(truncated)"

        # AI response completed
        Thread(
            target=send_to_zapier,
            args=(
                question,
                responseToZaiper,
                selected_model,
                session_id
            ),
            daemon=True
        ).start()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )