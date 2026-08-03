"use client";

import { useState } from "react";
import { useLoading } from "@/context/LoadingContext"
import ChatBox from "@/components/ChatBox";
import ProtectedRoute from "@/components/ProtectedRoute";
import Sidebar from "@/components/Sidebar";


export default function Home() {

  const { setGlobalLoading } = useLoading()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [error, setError] = useState("");

  return (
    <ProtectedRoute>
      <div className="flex h-screen overflow-hidden">
        <Sidebar mode="chat" collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
        <div className="flex-1 bg-slate-100 p-4 min-w-0">
          {error && (
            <div className="mb-3">
              <p className="text-red-500">
                {error}
              </p>
            </div>
          )}
          <ChatBox />
        </div>
      </div>
    </ProtectedRoute>
  );
}