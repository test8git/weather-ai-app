# ==========================================
# Standard Library
# ==========================================

import base64
import json
import mimetypes
import subprocess
import traceback

from datetime import datetime
from zoneinfo import ZoneInfo

import os
from dotenv import load_dotenv
from pathlib import Path

# ==========================================
# Third Party
# ==========================================

import cv2
from PIL import Image

from langgraph.prebuilt import create_react_agent

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

# ==========================================
# Services
# ==========================================

from services.llm_factory import get_llm
from services.image_service import analyze_image
from services.transcribe_service import transcribe_audio

from services.html_builder import *

# ==========================================
# Prompts
# ==========================================

from common.system_prompt import render_system_prompt
from common.error_formatter import format_ai_error

# ==========================================
# STREAM
# ==========================================

from stream.context import StreamContext
from stream.progress import progress_manager
from stream.stream_runner import stream_runner

# ==========================================
# Local Tools
# ==========================================

from tools.multi_tool import (
    search_web,
    get_weather,
    current_time,
    search_news,
    wikipedia_search,
    programming_search,
    search_finance,
)

from tools.calculator_tool import calculate_expression
from tools.github_tool import search_github
from tools.image_tool import generate_image
from tools.places_tool import search_places
from tools.file_tool import read_file_content


# ==========================================
# SUPABASE
# ==========================================

from supabase import create_client

# ==========================================
# ContextVar
# ==========================================

from common.request_context import (current_user_id, current_profile, current_selected_ai_modal)

# ==========================================
# MCP / Zapier
# ==========================================

from zapier.zapier_tool import zapier_action

# Load .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


CHART_KEYWORDS = {
    "chart",
    "graph",
    "plot",
    "pie",
    "bar chart",
    "line chart",
    "scatter",
    "visualize",
}
DEBUG_STREAM = False

MAX_IMAGE_SIZE = (1024, 1024)

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def need_chart(question: str) -> bool:
    q = question.lower()
    return any(word in q for word in CHART_KEYWORDS)

def sse_event(event_type: str, content):

    if DEBUG_STREAM:
        print(event_type)
        print(content)

    return (
        json.dumps(
            {
                "type": event_type,
                "content": content,
            }
        )
        + "\n\n"
    )

def sse_step(step, status, icon):

    data = {
        "type": "step",
        "step": step,
        "status": status,
        "icon": icon
    }

    return f"{json.dumps(data)}\n\n"

# ============================================================
# Graph Builder
# ============================================================

def create_agent_graph(
    provider: str,    
    currentDate: str,
    currentWeekDay: str,
    currentTime: str,
    llm:None,
    available_tools: dict,
    conversation_history=None,
    enable_chart: bool = False,
    mcp_connected: bool = False,
):
    """
    Create a LangGraph ReAct agent.

    Parameters
    ----------
    provider
        LLM Provider
        (Gemini/OpenAI/Groq/OpenRouter)

    conversation_history
        Previous conversation from Supabase

    enable_chart
        Whether chart instructions should be injected into the prompt.
    """

    system_prompt = render_system_prompt(
        currentDate=currentDate,
        currentWeekDay=currentWeekDay,
        currentTime=currentTime,
        conversation_history=conversation_history,
        enable_chart=enable_chart,
        mcp_connected=mcp_connected,
    )

    # print("SYSTEM_PROMPT : ")
    # print(system_prompt)

    # print("======================")
    # print("AVAILABLE_TOOLS NEW : ")
    # for t in available_tools:
    #     print(t.name)

    graph = create_react_agent(
        llm,
        available_tools,
        prompt=system_prompt,
    )

    return graph

# ============================================================
# Message Preparation
# ============================================================

def prepare_messages(
    question: str,
    file_path: str | None = None,
    content_type: str | None = None,
    llm=None,
):
    """
    Build LangChain messages from the user's question and optional uploaded file.

    Supports:

        - Text
        - Image
        - Audio
        - Video
        - PDF
        - DOCX
        - PPTX
        - XLSX
        - CSV
        - TXT
        - RTF
    """

    #
    # No uploaded file
    #
    if not file_path:

        return [
            HumanMessage(content=question)
        ]

    #
    # Read uploaded file
    #
    file_data = read_file_content(
        file_path,
        content_type,
        llm,
    )

    #
    # IMAGE
    #
    if file_data["type"] == "image":

        image_path = file_data["content"]

        image_analysis = analyze_image(
            image_path,
            llm,
            question,
        )

        return [
            HumanMessage(
                content=f"""
                User Question:

                {question}

                Image Analysis:

                {image_analysis}
                """
            )
        ]

    #
    # AUDIO
    #
    if file_data["type"] == "audio":

        transcript = transcribe_audio(file_data["content"])

        return [
            HumanMessage(
                content=f"""
                User Question:

                {question}

                Audio Transcript:

                {transcript}
                """
            )
        ]

    #
    # VIDEO
    #
    if file_data["type"] == "video":

        video_path = file_data["content"]

        audio_path = video_path + ".mp3"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-q:a",
                "0",
                "-map",
                "a",
                audio_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        transcript = transcribe_audio(
            audio_path
        )

        frame_analysis = []

        video = cv2.VideoCapture(video_path)

        frame_count = 0

        while True:

            success, frame = video.read()

            if not success:
                break

            #
            # Every 150th frame
            #
            if frame_count % 150 == 0:

                frame_path = f"_frame_{frame_count}.jpg"

                cv2.imwrite(
                    frame_path,
                    frame,
                )

                try:

                    result = analyze_image(
                        frame_path,
                        llm,
                        "Describe this frame.",
                    )

                    frame_analysis.append(result)

                finally:

                    if os.path.exists(frame_path):
                        os.remove(frame_path)

            frame_count += 1

        video.release()

        if os.path.exists(audio_path):
            os.remove(audio_path)

        return [
            HumanMessage(
                content=f"""
                User Question:

                {question}

                Video Transcript:

                {transcript}

                Frame Analysis:

                {chr(10).join(frame_analysis)}

                Please answer the user's question using both the transcript and the visual analysis.
                """
            )
        ]

    #
    # DOCUMENTS
    #
    if file_data["content"]:

        return [
            HumanMessage(
                content=f"""
                User Question:

                {question}

                Uploaded File:

                {file_data["content"]}

                If the uploaded file contains instructions,
                assignments,
                questions,
                code,
                or documents,

                use them to answer the user's request.
                """
            )
        ]

    #
    # Fallback
    #
    return [
        HumanMessage(content=question)
    ]


# ============================================================
# Chart Helper
# ============================================================

def should_enable_chart(
    question: str,
) -> bool:

    return need_chart(question)


# ============================================================
# File Helper
# ============================================================

SUPPORTED_FILE_TYPES = (
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".csv",
    ".txt",
    ".rtf",
)


def should_use_file_reader(
    filename: str | None,
):

    if not filename:
        return False

    filename = filename.lower()

    return filename.endswith(
        SUPPORTED_FILE_TYPES
    )


async def run_agent_stream(current_question, history, session_id, selected_model, conversation_id, file_path=None, content_type=None):

    answer = ""

    yield progress_manager.thinking_started_fun()["sse"]

    try:

        currentDate = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).strftime("%Y-%m-%d")

        currentWeekDay = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).strftime("%A")

        currentTime = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).strftime("%H:%M:%S")

        #
        # Create graph
        #

        enable_chart = should_enable_chart(current_question)

        # ==========================================
        # Available Tools
        # ==========================================

        available_tools = [

            # Search
            search_web,
            search_news,
            wikipedia_search,
            programming_search,
            search_finance,

            # Utility
            calculate_expression,
            current_time,

            # Weather
            get_weather,

            # Images
            generate_image,

            # GitHub
            search_github,

            # Maps
            search_places,
        ]

        # save user_id to ContextVar
        current_user_id.set(session_id)

        profile = supabase.table("profiles").select("mcp_url,mcp_connected").eq("id",session_id).single().execute()

        current_profile.set(profile.data)
        current_selected_ai_modal.set(selected_model)
        
        # print("PROFILE : ")
        # print(profile.data)

        mcp_connected = False
        if profile.data:
            mcp_connected = profile.data.get("mcp_connected", False)
        
        if mcp_connected:
            available_tools.append(zapier_action)
        
        llm = get_llm(selected_model)

        graph = create_agent_graph(
            provider=selected_model,
            currentDate=currentDate,
            currentWeekDay=currentWeekDay,
            currentTime=currentTime,
            llm=llm,
            available_tools=available_tools,
            conversation_history=history,
            enable_chart=enable_chart,
            mcp_connected=mcp_connected
        )

        yield progress_manager.thinking_completed_fun()["sse"]

        messages = history + prepare_messages(question=current_question, file_path=file_path, content_type=content_type, llm=llm)

        yield progress_manager.analyzing_started_fun()["sse"]
        
        #
        # Create stream context
        #

        ctx = StreamContext(
            current_question=current_question,
        )

        #
        # Start graph
        #

        async for event in graph.astream_events(
            {
                "messages": messages
            },
            version="v2",
        ):
            
            # print("\n================ STREAM EVENT ================")
            # print("EVENT TYPE:", event.get("event"))
            # print("NAME:", event.get("name"))
            # print("DATA:", event.get("data"))
            # print("METADATA:", event.get("metadata"))
            # print("==============================================\n")

            events = await stream_runner.process(event, ctx)

            #
            # Send SSE events
            #

            for event in events:
                
                #
                # Collect final answer
                #
                if isinstance(event, str):
                    yield event
                    continue

                if event.get("type") == "token":
                    answer += event["content"]

                yield event["sse"]
            

            # Do not break the LangGraph event stream here.
            # The final AI response may arrive after the tool result.
            
            # if ctx.result_generated or ctx.finished:
            #     break

        #
        # Final progress
        #

        yield progress_manager.generating_completed_fun()["sse"]
        
        # return answer
        return

    except Exception as e:

        traceback.print_exc()

        if hasattr(e, "body"):
            print("BODY")
            print(e.body)

        if hasattr(e, "response"):
            print("RESPONSE")
            print(e.response)

        error_message = str(e)

        print(error_message)

        yield sse_event(
            "error",
            error_message,
        )

        # yield sse_event(
        #     "error",
        #     format_ai_error(e),
        # )
