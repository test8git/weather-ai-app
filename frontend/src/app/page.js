"use client";

import { useState } from "react";
import { useLoading } from "@/context/LoadingContext"
import ChatBox from "@/components/ChatBox";


export default function Home() {

  const { setGlobalLoading } = useLoading()
  const [error, setError] = useState("");

  return (
    <div className="min-h-screen bg-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-3xl shadow-xl p-4 md:p-8">
            {error && (
              <div>
                <p className="text-red-500 mt-4">
                  {error}
                </p>
              </div>
            )}
          
          <div>            
            <ChatBox />
          </div>
        </div>
      </div>
    </div>
  );
}