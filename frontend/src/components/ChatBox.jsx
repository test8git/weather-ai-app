"use client";

import { useState } from "react";
import { useLoading } from "@/context/LoadingContext"

export default function ChatBox() {

  const [question, setQuestion] = useState("");
  // const [city, setCity] = useState("");
  const { setGlobalLoading } = useLoading();
  const [messages, setMessages] = useState([]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      askAI();
    }
  };

  const askAI = async () => {

    try 
    {
        // if (!city.trim()) {
        //     alert("Please enter city");
        //     return;
        // }
        if (!question.trim()) {
            alert("Please enter your question");
            return;
        }

        const session_id = "user-123";

        setGlobalLoading(true)

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {

        method: "POST",

        headers: {
            "Content-Type": "application/json",
        },

          body: JSON.stringify({
              question:question,
              session_id:session_id
          }),
        });

        const data = await response.json();

        var _answer = "";

        if(Array.isArray(data.answer))
        {
            _answer = data.answer[0].text;
        }
        else{
          _answer = data.answer;
        }

        setMessages(prev => [
          ...prev,
          { role: "user", content: question },
          { role: "assistant", content: _answer }
        ]);

        setQuestion("");

        setAnswer(_answer);

        // speakText(_answer);
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

    <div className="bg-white rounded-3xl shadow p-4 md:p-5 mt-6">

      <h2 className="text-2xl font-bold mb-4">
        AI Weather Assistant
      </h2>

      {messages && (

        <div className="space-y-4 mt-2 mb-3">

            {messages.map((msg, index) => (

                <div key={index} className={msg.role === "user"? "text-right": "text-left"}>

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

      <div className="flex flex-col gap-3">
        <div className="flex flex-col md:flex-row gap-3">
          {/* <input
                  type="text"
                  placeholder="Enter city"
                  className="border p-3 rounded-xl"
                  value={city} onChange={(e) => setCity(e.target.value)}
                /> */}

          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about weather..."
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