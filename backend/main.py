from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from graph.agent_graph import run_agent

app = FastAPI()

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


@app.post("/chat")
def chat(req: ChatRequest):

    # response = graph.invoke({
    #     "messages": [
    #         ("user", req.question)
    #     ]
    # })



    # response = graph.invoke({
    #     "question": req.question,
    #     "session_id": req.session_id
    # })


    answer = run_agent(
        req.question,
        req.session_id
    )

    return {
        "answer": answer
    }