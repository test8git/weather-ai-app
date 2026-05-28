from database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from graph.agent_graph import run_agent
from graph.agent_graph import run_agent_stream

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


@app.post("/chat")
def chat(req: ChatRequest):

    # async def generate():
    #     answer = run_agent(
    #         req.question,
    #         req.session_id
    #     )

    #     # STREAM CHARACTER BY CHARACTER
    #     for char in answer:
    #         yield char
    #         await asyncio.sleep(0.02)

    # return StreamingResponse(
    #     generate(),
    #     media_type="text/plain"
    # )

    async def generate():
        for chunk in run_agent_stream(
            req.question,
            req.session_id,
            req.selected_model
        ):

            # SSE FORMAT
            yield f"data: {chunk}\n\n"

            await asyncio.sleep(0.02)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )