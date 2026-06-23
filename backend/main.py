import os
import uuid
from database import init_db
from fastapi import FastAPI, UploadFile, File, Form
import tempfile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from graph.agent_graph import run_agent_stream
from services.transcribe_service import transcribe_audio

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
        for chunk in run_agent_stream(
            question,
            session_id,
            selected_model,
            file_path,
            content_type
        ):

            # SSE FORMAT
            yield f"data: {chunk}\n\n"

            await asyncio.sleep(0.02)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )