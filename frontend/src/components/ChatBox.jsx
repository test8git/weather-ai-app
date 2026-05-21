"use client";

import { useState } from "react";
import { useLoading } from "@/context/LoadingContext"

export default function ChatBox({ city, forecast }) {

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const { setGlobalLoading } = useLoading();
  const [messages, setMessages] = useState([]);

  const askAI = async (inputQuestion = question) => {

    try 
    {
        if (!inputQuestion.trim()) {
            alert("Please enter your question");
            return;
        }

        // Add user message
        const userMessage = {
            role: "user",
            content: inputQuestion
        }

        setMessages(prev => [...prev, userMessage])

        setGlobalLoading(true)

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {

        method: "POST",

        headers: {
            "Content-Type": "application/json",
        },

        body: JSON.stringify({
            city:city,
            question:inputQuestion,
            forecast:forecast
        }),
        });

        const data = await response.json();

        const aiMessage = {
        role: "assistant",
        content: data.answer
        }

        setMessages(prev => [...prev, aiMessage])

        setAnswer(data.answer);

        speakText(data.answer);
    }
    catch(error)
    {

    }
    finally 
    {
      setGlobalLoading(false)
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

        console.log(transcript);

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

    <div className="bg-white rounded-3xl shadow p-5 mt-6">

      <h2 className="text-2xl font-bold mb-4">
        AI Weather Assistant
      </h2>

      <div className="flex gap-3">

        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about weather..."
          className="border p-3 rounded-xl flex-1"
        />
        <button onClick={startListening} className="bg-blue-600 text-white px-5 rounded-xl">🎤 Speak</button>
        <button onClick={askAI} className="bg-blue-600 text-white px-5 rounded-xl">Ask</button>

      </div>
      
      {/* {answer && (

        <div className="mt-5 bg-gray-100 p-4 rounded-xl whitespace-pre-wrap">

          {answer}

        </div>
      )} */}

      {messages && (

        <div className="space-y-4 mt-2">

            {messages.map((msg, index) => (

                <div
                key={index}
                className={
                    msg.role === "user"
                    ? "text-right"
                    : "text-left"
                }
                >

                <div
                    className={
                    msg.role === "user"
                        ? "bg-blue-500 text-white inline-block p-3 rounded-xl"
                        : "bg-gray-200 text-black inline-block p-3 rounded-xl"
                    }
                >

                    {msg.content}

                </div>

                </div>

            ))}

            </div>
      )}

    </div>
  );
}