"use client";

import { useState } from "react";
import { useLoading } from "@/context/LoadingContext"

export default function ChatBox({ city, forecast }) {

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const { setGlobalLoading } = useLoading();
  const [messages, setMessages] = useState([]);

  const askAI = async () => {

    try 
    {
        if (!question.trim()) {
            alert("Please enter your question");
            return;
        }

        // Add user message
        const userMessage = {
            role: "user",
            content: question
        }

        setMessages(prev => [...prev, userMessage])

        setGlobalLoading(true)

        const response = await fetch("http://127.0.0.1:8000/chat", {

        method: "POST",

        headers: {
            "Content-Type": "application/json",
        },

        body: JSON.stringify({
            city,
            question,
            forecast
        }),
        });

        const data = await response.json();

        const aiMessage = {
        role: "assistant",
        content: data.answer
        }

        setMessages(prev => [...prev, aiMessage])

        setAnswer(data.answer);
    }
    catch(error)
    {

    }
    finally 
    {
      setGlobalLoading(false)
    }
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

        <button
          onClick={askAI}
          className="bg-blue-600 text-white px-5 rounded-xl"
        >
          Ask
        </button>

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