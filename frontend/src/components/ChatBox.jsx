"use client";

import { useEffect, useRef, useState } from "react";
import { useLoading } from "@/context/LoadingContext"
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function ChatBox() {

  const [question, setQuestion] = useState("");
  // const [city, setCity] = useState("");
  const { setGlobalLoading } = useLoading();
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("");
  const messagesEndRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState("");

  const session_id = "user-123";

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth"
    });
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      askAI();
    }
  };

  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const askAI = async () => {

    try 
    {
        // if (!city.trim()) {
        //     alert("Please enter city");
        //     return;
        // }
        if (!selectedModel.trim()) {
            alert("Please select AI modal");
            return;
        }
        if (!question.trim()) {
            alert("Please enter your question");
            return;
        }

        const userMessage = {
          role: "user",
          content: question
        };

        setMessages((prev) => [...prev, userMessage]);

        //////setGlobalLoading(true)

        //setStatus("Thinking...");

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {

        method: "POST",

        headers: {
            "Content-Type": "application/json",
        },

          body: JSON.stringify({
              question:question,
              session_id:session_id,
              selected_model: selectedModel
          }),
        });

        if (!response.body) {
          throw new Error("No response body");
        }

        //await delay(500);

        //setStatus("Analyzing response...");

        //const data = await response.json();

        // EMPTY AI MESSAGE
        let aiMessage = {
          role: "assistant",
          content: ""
        };

        setMessages((prev) => [...prev, aiMessage]);

        const reader = response.body.getReader();

        const decoder = new TextDecoder();

        let done = false;

        //await delay(500);
        
        //setStatus("Generating final answer...");

        //await delay(500);

        while (!done) {
          const result = await reader.read();

          //console.log(result);

          done = result.done;
          // const chunk = decoder.decode(result.value || new Uint8Array(), {
          //   stream: true,
          // });

          const chunk = decoder.decode(result.value || new Uint8Array(), {
            stream: true,
          });

          const lines = chunk.split("\n");

          // const cleanChunk = chunk
          //   .replace(/data:\s*/g, "")
          //   .replace(/\n\n/g, "");

          //console.log("CLEAN:", cleanChunk);

          for (const line of lines) 
          {
            if (line.startsWith("data: "))
            {
                const jsonStr = line.replace("data: ", "");
                try {
                  const data = JSON.parse(jsonStr);

                  //console.log("EVENT:", data);

                  // STATUS
                  if (data.type === "status") {

                    setStatus(data.content);
                  }
                   // MESSAGE
                  else if (data.type === "message") {

                    aiMessage.content += data.content;

                    setMessages((prev) => {

                      const updated = [...prev];

                      updated[updated.length - 1] = {
                        ...aiMessage
                      };

                      return updated;
                    });
                  }

                  // ERROR
                  else if (data.type === "error") {

                    setStatus("");

                    aiMessage.content += "\n❌ " + data.content;
                  }
                } catch (err) {
                  console.error("JSON Parse Error", err);
                }
                
            }
          }
        }

        

        // var _answer = "";

        // if(Array.isArray(data.answer))
        // {
        //   alert("Array");
        //     _answer = data.answer[0].text;
        // }
        // else{
        //   _answer = data.answer;
        // }

        // setMessages(prev => [
        //   ...prev,
        //   { role: "user", content: question },
        //   { role: "assistant", content: _answer }
        // ]);

        // setQuestion("");

        // setAnswer(_answer);

        // speakText(_answer);
    }
    catch(error)
    {
      //console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Something went wrong."
        }
      ]);
    }
    finally 
    {
      //////setGlobalLoading(false)
      setStatus("");
    }
  };

  const startListening = () => 
  {

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert("Speech Recognition not supported in this browser");

        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-US";

    recognition.onresult = (event) => {

        const transcript = event.results[0][0].transcript;

        //console.log(transcript);

        setQuestion(transcript);

        askAI(transcript);
    };

    recognition.start();
  };
  
  const speakText = (text) => 
  {

    const speech = new SpeechSynthesisUtterance(text);

    speech.lang = "en-US";

    window.speechSynthesis.speak(speech);
  };

  return (

    <div className="bg-white rounded-3xl shadow p-4 md:p-5 mt-6">

      <h2 className="text-2xl font-bold mb-4">
        General AI Assistant
      </h2>

      {messages && (

        <div className="space-y-4 mt-2 mb-3">

            {messages.map((msg, index) => (

                <div key={index} className={msg.role === "user"? "text-right": "text-left"}>

                  <div
                      className={
                      msg.role === "user"
                          ? "bg-blue-500 text-white inline-block p-3 rounded-xl"
                          : "bg-gray-200 text-black inline-block p-3 rounded-xl w-full"
                      }
                  >
                    <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              pre: ({ children }) => (
                                <pre className="whitespace-pre-wrap break-wordsoverflow-x-autobg-gray-200 p-4 rounded-xl">
                                  {children}
                                </pre>
                              )
                            }}
                          >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
            ))}
            </div>
      )}

      <div ref={messagesEndRef}></div>

      {status && (
        <div className="text-sm text-gray-500 mb-2 animate-pulse">
          {status}
        </div>
      )}

      <div className="flex flex-col gap-3">
        <div className="flex flex-col md:flex-row gap-3">
          {/* <input
                  type="text"
                  placeholder="Enter city"
                  className="border p-3 rounded-xl"
                  value={city} onChange={(e) => setCity(e.target.value)}
                /> */}

          <select className="border p-3 rounded-xl" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              <option value="">Select AI Modal</option>
              <option value="gemini">Gemini</option>
              <option value="openai">OpenAI</option>
              <option value="claude">Claude</option>
              <option value="grok">Grok</option>
              <option value="openrouter">OpenRouter</option>
              <option value="groq">Groq</option>
            </select>

          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything..."
            className="border p-3 rounded-xl w-full"
          />
        </div>
        <div className="flex justify-end gap-3">
          {/* <button onClick={startListening} className="bg-blue-600 text-white px-5 py-3 rounded-xl">🎤 Speak</button> */}
          <button onClick={() => askAI()} className="bg-blue-600 text-white px-5 py-3 rounded-xl">Ask</button>
        </div>
      </div>
      
      {/* {answer && (

        <div className="mt-5 bg-gray-100 p-4 rounded-xl whitespace-pre-wrap">

          {answer}

        </div>
      )} */}

      

    </div>
  );
}