"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useConversation } from "@/context/ConversationProvider";
import { useAuth } from "@/context/AuthProvider";
import { useLoading } from "@/context/LoadingContext"
import { EllipsisVerticalIcon } from "@heroicons/react/24/outline";

export default function Sidebar() {
    const { setGlobalLoading } = useLoading();
    const { user } = useAuth();
    const { conversationId, setConversationId, setMessages, setNewChatTrigger, conversations, setConversations} = useConversation();
    
    const [menuOpenId, setMenuOpenId] = useState(null);

    const [editingId, setEditingId] = useState(null);
    const [editingTitle, setEditingTitle] = useState("");
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [conversationToDelete, setConversationToDelete] = useState(null);

    const menuRef = useRef(null);

    const router = useRouter();

    useEffect(() => {
        if (user)
        {
            loadConversations();
        }
    }, [user]);

    //Close Menu (three-dot menu) When Clicking Outside
    useEffect(() => {

        const handleClickOutside = (event) => {

            if (menuRef.current && !menuRef.current.contains(event.target))
            {
                setMenuOpenId(null);
            }
        };

        document.addEventListener(
            "mousedown",
            handleClickOutside
        );

        return () => {
            document.removeEventListener(
                "mousedown",
                handleClickOutside
            );
        };

    }, []);

    const loadConversations = async () =>
    {
        try
        {
            setGlobalLoading(true);
            const { data, error } =
                await supabase
                    .from("conversations")
                    .select("*")
                    .eq("user_id", user.id)
                    .order(
                        "created_at",
                        {
                            ascending: false
                        }
                    );

            if (error)
            {
                console.error(error);
                return;
            }

            setConversations(data);
        }
        finally
        {
            setGlobalLoading(false);
        }
    };

    const createNewChat = async () =>
    {
        setConversationId(null);
        // Clear current chat
        setMessages([]);

        setNewChatTrigger(
          prev => prev + 1
        );
    };

    const deleteConversation = async (id) =>
    {
        // const confirmed = window.confirm(
        //     "Delete this conversation?"
        // );

        // if (!confirmed)
        //     return;

        if (!conversationToDelete)
            return;

        try
        {
            setGlobalLoading(true);
            const { error } = await supabase.from("conversations").delete().eq("id", conversationToDelete);

            if (error)
            {
                console.error(error);

                return;
            }

            if (conversationId === conversationToDelete)
            {
                setConversationId(null);
                setMessages([]);
            }

            setDeleteModalOpen(false);
            setConversationToDelete(null);
            loadConversations();
        }
        finally
        {
            setGlobalLoading(false);
        }
    };

    const renameConversation = async (id, currentTitle) =>
    {
        const newTitle =
            prompt(
                "Enter new title",
                currentTitle
            );

        if(!newTitle || !newTitle.trim())
            return;

        try
        {
            setGlobalLoading(true);
            const { error } =
                await supabase
                    .from("conversations")
                    .update({
                        title: newTitle.trim()
                    })
                    .eq("id", id);

            if (error)
            {
                console.error(error);
                return;
            }

            loadConversations();
        }
        finally
        {
            setGlobalLoading(false);
        }
    };

    const openConversation = async (conversationId) =>
    {
        try
        {
            setGlobalLoading(true);
            setConversationId(conversationId);
        }
        finally
        {
            setGlobalLoading(false);
        }
    };

    const logout = async () => {
        setGlobalLoading(true);
        await supabase.auth.signOut();
        setGlobalLoading(false);
        router.push("/login");
    };

    return (

        <div className="w-72 bg-slate-900 text-white flex flex-col">

            {/* Logo */}
            <div className="p-6 border-b border-slate-700">

                <h1 className="text-2xl font-bold">
                    General AI Assistant
                </h1>

            </div>

            {/* New Chat */}
            <div className="p-4">

                <button onClick={createNewChat} className="w-full bg-slate-800 hover:bg-slate-700 rounded-xl py-3">
                    + New Chat
                </button>
            </div>

            {/* History */}
            <div className="flex-1 px-4 overflow-y-auto">

                <div className="text-sm text-slate-400 mb-3">
                    Recent Chats
                </div>

                <div className="space-y-2">

                    {conversations.map((conv) => (
                        <div key={conv.id} className={`group relative flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer
                                    ${conversationId === conv.id ? "bg-slate-700" : "hover:bg-slate-800" } `}>
                            {/* Conversation Title */}
                            <div className="flex-1 truncate" onClick={() => openConversation(conv.id)}>
                                {conv.title}
                            </div>
                            
                            {/* Three Dot Menu */}
                            <button onClick={(e) => {
                                    e.stopPropagation();
                                    setMenuOpenId(menuOpenId === conv.id ? null : conv.id );
                                }}
                                className={`cursor-pointer px-2 ${menuOpenId === conv.id ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                                    <EllipsisVerticalIcon className="w-5 h-5" />
                            </button>

                            {/* Popup Menu */}
                            {menuOpenId === conv.id && (
                                <div ref={menuOpenId === conv.id ? menuRef : null} 
                                     className="absolute right-2 top-10 z-50 bg-white border rounded-xl shadow-lg w-36">

                                    <button
                                        className="cursor-pointer block w-full text-left p-1 text-blue-500"
                                        onClick={() => {
                                            setMenuOpenId(null);
                                            renameConversation(conv.id, conv.title);
                                        }}
                                    >
                                        ✏️ Rename
                                    </button>

                                    <button
                                        className="cursor-pointer block w-full text-left p-1 text-red-500"
                                        onClick={() => {
                                            setMenuOpenId(null);
                                            setConversationToDelete(conv.id);
                                            setDeleteModalOpen(true);
                                        }}
                                    >
                                        🗑 Delete
                                    </button>

                                </div>
                            )}

                            
                        </div>
                    ))}

                </div>
{/* 
                <div className="space-y-2">

                    <button className="w-full text-left p-3 rounded-lg hover:bg-slate-800">
                        Weather Forecast
                    </button>

                    <button className="w-full text-left p-3 rounded-lg hover:bg-slate-800">
                        IPL Analysis
                    </button>

                    <button className="w-full text-left p-3 rounded-lg hover:bg-slate-800">
                        Stock Prediction
                    </button>

                </div> */}

            </div>

            {/* User */}
            <div className="border-t border-slate-700 p-4">

                <div className="text-sm mb-2 truncate">
                    {user?.email}
                </div>

                <button
                    onClick={logout}
                    className="w-full bg-red-500 hover:bg-red-600 rounded-xl py-2"
                >
                    Logout
                </button>

            </div>

            {/* Delete Conversation Modal */}
            {deleteModalOpen && (

                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
                        <h2 className="text-xl font-semibold text-gray-800 mb-2">
                            Delete Conversation
                        </h2>
                        <p className="text-gray-600 mb-6">
                            Are you sure you want to delete this conversation?
                        </p>
                        <div className="flex justify-end gap-3">
                            <button onClick={() => {
                                    setDeleteModalOpen(false);
                                    setConversationToDelete(null);
                                }}
                                className="px-4 py-2 rounded-xl border border-gray-300 bg-gray-500 hover:bg-gray-900"
                            >
                                Cancel
                            </button>

                            <button
                                onClick={deleteConversation}
                                className="px-4 py-2 rounded-xl bg-red-500 text-white hover:bg-red-600"
                            >
                                Delete
                            </button>

                        </div>

                    </div>

                </div>

            )}

        </div>
    );
}