from langgraph.prebuilt import create_react_agent

import base64
import mimetypes
from PIL import Image
from langchain_core.messages import HumanMessage
from services.llm_factory import get_llm
from tools.multi_tool import search_web, get_weather, current_time, search_news, wikipedia_search, search_programming, search_finance
from tools.image_tool import generate_image
from tools.places_tool import search_places
from tools.github_tool import search_github
from tools.calculator_tool import calculate_expression
from tools.memory_tool import save_message, get_history
from tools.file_tool import read_file_content
from services.transcribe_service import transcribe_audio
from services.image_service import analyze_image
from common.error_formatter import format_ai_error
import subprocess
import cv2
from datetime import datetime
from zoneinfo import ZoneInfo

import json
from langchain_core.messages import ToolMessage, AIMessage
from services.html_builder import *


# Give the AI access to this tool/function
tools = [search_web, get_weather, calculate_expression, current_time, search_news, wikipedia_search, search_programming, search_finance, generate_image, search_places, search_github]

def sse_event(event_type, content):

    print("sse_event : ")
    print(event_type)
    print(content)

    return f"{json.dumps({
        "type": event_type,
        "content": content
    })}\n\n"

def sse_step(step, status, icon):

    data = {
        "type": "step",
        "step": step,
        "status": status,
        "icon": icon
    }

    return f"{json.dumps(data)}\n\n"


def need_chart(question):

    chart_keywords = [
        "chart",
        "graph",
        "plot",
        "pie",
        "bar chart",
        "line chart",
        "scatter",
        "visualize"
    ]

    q = question.lower()

    return any(keyword in q for keyword in chart_keywords)    


def run_agent_stream(question, session_id, selected_model, file_path=None, content_type=None):

    print("Calling : run_agent_stream")

    currentDate = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    currentWeekDay = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%A")
    currentTime = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")

    yield sse_step(
        "Thinking...",
        "running",
        "🧠"
    )

    # Create LLM Dynamically
    llm = get_llm(selected_model)

    chart_prompt = ""
    if need_chart(question):
        chart_prompt = """
            ========================
            CHARTS
            ========================

            If the user asks for:

            - chart
            - graph
            - trend
            - plot
            - visualization
            - dashboard
            - stock chart
            - sales chart
            - revenue chart

            Return ONLY a chart block.

            Example:

            ```chart
            {
            "type":"line",
            "title":"Sample Chart",
            "xKey":"date",
            "series":[
                {
                "name":"Value",
                "dataKey":"value"
                }
            ],
            "data":[
                {
                "date":"Mon",
                "value":10
                },
                {
                "date":"Tue",
                "value":20
                }
            ]
            }
        """

    system_prompt = f"""

    You are a professional AI assistant.

    Current timezone:
    Asia/Kolkata

    Today's date:
    {currentDate}

    Current weekday:
    {currentWeekDay}

    Current time:
    {currentTime}

    ========================
    GENERAL BEHAVIOR
    ========================

    - Respond directly with the final answer.
    - Never reveal internal reasoning.
    - Never explain your thinking process.
    - Never narrate actions.
    - Never mention tools.
    - Never say:
        - "Let me check..."
        - "Searching..."
        - "Using tool..."
        - "I will use..."
        - "I need to search..."
    - Be concise but complete.
    - If the user requests detailed information, provide a detailed answer.
    - Use Markdown formatting where appropriate.
    - Use tables when they improve readability.

    ========================
    TOOL USAGE
    ========================

    When external, live, or changing information is required, ALWAYS use the appropriate tool.

    Examples include:

    - Current weather
    - News
    - Sports
    - Stock prices
    - Exchange rates
    - Company information
    - Recent events
    - Current date/time
    - Live information
    - Internet searches

    Never answer these from memory if a tool is available.

    Do not tell the user that you are using a tool.

    ========================
    PROGRAMMING
    ========================

    When the user asks for programming help:

    1. Briefly explain the solution.
    2. Return complete working code.
    3. Put every code snippet inside Markdown fenced blocks.
    4. Always specify the language.
    5. Include useful comments.
    6. If multiple files are needed, separate them with headings.
    7. For C#, target .NET 8 unless specified otherwise.
    8. For SQL, include CREATE TABLE statements if relevant.
    9. Prefer official documentation.
    10. Use Stack Overflow for practical solutions.
    11. Use GitHub for real-world examples.
    12. Use programming search automatically whenever external information is useful.
    13. Never mention that you searched.

    ======================
    Finance
    ======================

    Whenever the user asks about:

    - stock
    - share
    - company price
    - market cap
    - dividend
    - PE ratio
    - earnings
    - trading volume

   If the user asks about:

    - earnings
    - EPS
    - revenue
    - analyst estimates
    - earnings surprise
    - beat / miss
    - quarterly results

    NEVER search using only:

    "Apple earnings history"

    Instead search using

    "<ticker> earnings surprise"
    "<ticker> quarterly EPS actual estimate"
    "<ticker> earnings actual vs estimate"
    "<ticker> EPS consensus" 

    always use the search_finance tool.

    Never use general web search if finance data is available.

    ======================
    News
    ======================

    Use search_news whenever the user asks about:

    - news
    - today's news
    - latest news
    - breaking news
    - politics
    - sports
    - elections
    - AI news
    - business news
    - market news
    - current events

    Always use search_news instead of search_web when the user is requesting recent news.

    =======================
    SEARCH PLACES
    =======================

    Use search_places whenever the user asks for:

    restaurants
    hotels
    hospitals
    ATMs
    petrol pumps
    tourist places
    cafes
    parks
    shopping malls
    schools
    colleges
    airports
    railway stations
    nearby places
    location
    address
    map

    ====================
    CALCULATE EXPRESSION
    ====================

    Use calculate_expression whenever the user asks for:

    - arithmetic
    - mathematics
    - percentage
    - square root
    - logarithm
    - factorial
    - trigonometry
    - powers
    - equations
    - calculations

    =======================
    Image Generation
    =======================

    Whenever the user asks to

    - generate image
    - create image
    - draw
    - paint
    - illustration
    - wallpaper
    - logo
    - icon

    call generate_image.

    Return the generated image.

    =======================
    GITHUB
    =======================

    For GitHub-related questions such as:

    - Find GitHub repository
    - Search GitHub
    - Open source project
    - Repository
    - GitHub library

    Always use the search_github tool.

    {chart_prompt}

    """
    
    # SAVE USER MESSAGE
    save_message(session_id, "user", question)

    answer = ""
    tool_name = ""

    # GET OLD HISTORY
    history = get_history(session_id)

    file_data = read_file_content(file_path, content_type, llm)

    file_prompt = ""

    if file_data["type"] == "image":
        try:
            yield sse_step(
                "Thinking...",
                "completed",
                "✔️"
            )

            yield sse_step(
                "Analyzing image...",
                "running",
                "🖼️"
            )

            imageResult = analyze_image(file_data["content"], llm, question)


            answer+=imageResult

            yield sse_step(
                "Analyzing image...",
                "completed",
                "✔️"
            )

            yield sse_event(
                "message",
                imageResult
            )

            save_message(session_id, "assistant", answer)

            return

        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # error_message = repr(e)

            # Format Error
            error_message = format_ai_error(e)

            answer += error_message

            yield sse_event("error", error_message)

    else:

        fileContent = ""
        frame_analysis = []

        # Audio file
        if file_data["type"] == "audio":
            transcript = transcribe_audio(file_data["content"])
            file_data["content"] = transcript
        
        # Video file
        if file_data["type"] == "video":
            video_path = file_data["content"]
            audio_path = video_path + ".mp3"

            subprocess.run([
                "ffmpeg",
                "-i", video_path,
                "-q:a", "0",
                "-map", "a",
                audio_path
            ])

            transcript = transcribe_audio(audio_path)
            file_data["content"] = transcript

            video = cv2.VideoCapture(video_path)

            frames = []

            count = 0

            while True:

                success, frame = video.read()

                if not success:
                    break

                if count % 150 == 0:

                    frame_path = f"frame_{count}.jpg"

                    cv2.imwrite(frame_path, frame)

                    frames.append(frame_path)

                count += 1

            video.release()


            for frame in frames:

                result = analyze_image(frame, llm, "Describe this image in detail.")

                frame_analysis.append(result)

        # print("*********************")
        # print(file_data["content"])


        if file_data["content"]:
            file_prompt = f"""
            IMPORTANT:

            If the file contains an instruction, prompt, question,
            essay topic, coding task, or assignment,
            perform the task.

            If the user asks to explain, summarize, analyze,
            review, or extract information,
            then analyze the file.

            Respond appropriately.
            """

            if file_data["type"] == "video":
                fileContent = f"""
                    Video Transcript:

                    {file_data["content"]}

                    Frame Analysis:

                    {frame_analysis}

                    Create a summary of this video.
                    """  
            else:
                fileContent = f"""
                    Uploaded File:
                    {file_data["content"]}
                    """

        # COMBINE HISTORY + NEW QUESTION
        full_prompt = f"""
        Conversation History:
        {history}

        User Question:
        {question}

        {fileContent}

        {file_prompt}
        """

        try:        

            yield sse_step(
                "Thinking...",
                "completed",
                "✔️"
            )

            
            # Create Graph Dynamically
            graph = create_react_agent(llm, tools, prompt=system_prompt)            

            # STATUS EVENT
            yield sse_step(
                "Analyzing your request...",
                "running",
                "🔍"
            )

            isAnalyzingCompleted = False
            isSearchingWeb = 0
            isResultGenerated = False
            isGeneratingStarted = False
            last_content = ""

            for message, metadata in graph.stream(
                {
                    "messages": [("user", full_prompt)]
                },
                stream_mode="messages"
            ):
                if not isAnalyzingCompleted:
                    yield sse_step(
                        "Analyzing your request...",
                        "completed",
                        "✔️"
                    )
                    isAnalyzingCompleted = True

                # TOOL STATUS
                node = metadata.get("langgraph_node", "")

                

                # DETECT TOOL
                if hasattr(message, "tool_calls"):

                    # TOOL STARTED
                    if (isSearchingWeb==0):                    
                        yield sse_step(
                            "Searching web...",
                            "running",
                            "🔍"
                        )
                        isSearchingWeb = 1

                    for tool_call in message.tool_calls:

                        tool_name = tool_call.get("name", "")

                        print("TOOL : ")
                        print(tool_name)

                if node == "agent" and not isGeneratingStarted:
                    # TOOL COMPLETED → BACK TO AGENT
                    
                    yield sse_step(
                        "Generating response...",
                        "running",
                        "✍️"
                    )
                    isGeneratingStarted = True

                # # # For image generation
                if isinstance(message, ToolMessage):
                    if (isSearchingWeb==1):
                        yield sse_step(
                            "Searching web...",
                            "completed",
                            "✔️"
                        )
                        isSearchingWeb = 2

                    try:
                        
                        if tool_name != "":
                            if tool_name == "generate_image" or tool_name == "calculate_expression" or tool_name == "search_github" or tool_name == "search_places":

                                tool_result = json.loads(message.content)

                                if tool_name == "calculate_expression":
                                    # pass
                                    tool_text = f"""
                                    Expression:
                                    {tool_result['expression']}
                                    Answer:
                                    {tool_result['result']}
                                    """

                                    answer = tool_text
                                    isResultGenerated = True
                                    yield sse_event("message", tool_text)
                                    continue

                                elif tool_name == "generate_image":

                                    if tool_result.get("type") == "image":
                                        isResultGenerated = True
                                        yield sse_event("image", tool_result["image_url"])
                                        continue

                                elif tool_name == "search_places":

                                    tool_text = ""
                                    items = []
                                    for place in tool_result["places"]:

                                        item_link = ""
                                        if place.get("google_maps"):
                                            item_link = hyperlink("Open Google Maps",place["google_maps"])
                                        elif place.get("url"):
                                            item_link = hyperlink("Open Link",place["url"])

                                        items.append(
                                            bold(place["name"])
                                            + line_break()
                                            + item_link
                                        )

                                    tool_text = heading(question)

                                    tool_text += ordered_list(items)

                                    answer = tool_text
                                    isResultGenerated = True
                                    yield sse_event("message", tool_text)
                                    continue

                                elif tool_name == "search_github":

                                    if tool_result.get("type") == "github":

                                        tool_text = ""

                                        for repo in tool_result["repositories"]:
                                            body = ""
                                            body += paragraph(repo["description"])
                                            body += bold(f"⭐ {repo['stars']}")
                                            body += line_break()
                                            body += hyperlink(
                                                "Open Repository",
                                                repo["url"]
                                            )

                                            tool_text += card(
                                                repo["full_name"],
                                                body
                                            )

                                        answer = tool_text
                                        isResultGenerated = True
                                        yield sse_event("message", tool_text)
                                        continue

                    except Exception:
                        pass

                    

                # STRING CONTENT
                if isResultGenerated == False and hasattr(message, "content"):
                    if (isSearchingWeb==1):
                        yield sse_step(
                            "Searching web...",
                            "completed",
                            "✔️"
                        )
                        isSearchingWeb = 2

                    content = message.content

                    # STRING CONTENT
                    if isinstance(content, str):

                        content = message.content

                        # clean_content = content.strip()
                        clean_content = content

                        if clean_content:
                            
                            # Skip duplicate content
                            if clean_content == last_content:
                                continue

                            last_content = clean_content

                            print("CLEAN CONTENT : " + clean_content)
                            print("LAST CONTENT : " + last_content)

                            answer += clean_content
                            yield sse_event("message", clean_content)


                    # LIST CONTENT (Gemini sometimes returns list)
                    elif isinstance(content, list):

                        for item in content:

                            if isinstance(item, dict):

                                text = item.get("text", "")

                                # clean_content = text.strip()
                                clean_content = text

                                if clean_content:

                                    answer += clean_content
                                    yield sse_event("message", clean_content)
                            

            # DONE
            # yield sse_event("status", "")

        except Exception as e:
            # import traceback
            # traceback.print_exc()
            # error_message = repr(e)

            # Format Error
            error_message = format_ai_error(e)

            answer += error_message

            print("ERROR : ")
            print(error_message)

            yield sse_event("error", error_message)

        save_message(session_id, "assistant", answer)

        yield sse_step(
            "Generating response...",
            "completed",
            "✔️"
        )


    print("ANSWER : ")
    print(answer)
    

    return answer

