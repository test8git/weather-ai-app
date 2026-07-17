"use client";

import { useEffect, useState, useRef } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useConversation } from "@/context/ConversationProvider";
import { useAuth } from "@/context/AuthProvider";
import { useLoading } from "@/context/LoadingContext"

import jsPDF from "jspdf";

import { EllipsisVerticalIcon, MagnifyingGlassIcon, ShareIcon, TrashIcon, ClockIcon } from "@heroicons/react/24/outline";
import { ArchiveBoxIcon, StarIcon } from "@heroicons/react/24/solid";

import dayjs from "dayjs";
import isToday from "dayjs/plugin/isToday";
import isYesterday from "dayjs/plugin/isYesterday";

dayjs.extend(isToday);
dayjs.extend(isYesterday);

export default function Sidebar({ mode = "chat" }) {
    const { setGlobalLoading } = useLoading();
    const { user } = useAuth();
    const { conversationId, setConversationId, messages, setMessages, setNewChatTrigger, conversations, setConversations, loadConversationMessages} = useConversation();
    
    const [menuOpenId, setMenuOpenId] = useState(null);

    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [conversationToDelete, setConversationToDelete] = useState(null);

    const [searchTerm, setSearchTerm] = useState("");

    const [showExportModal, setShowExportModal] = useState(false);
    const [selectedConversation, setSelectedConversation] = useState(null);
    const [exportType, setExportType] = useState("pdf");

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

    //Load recent Conversations
    const loadConversations = async () =>
    {
        try
        {
            //setGlobalLoading(true);
            const { data, error } =
                await supabase
                    .from("conversations")
                    .select("*")
                    .eq("user_id", user.id)
                    .eq("is_archived", false)
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
            //setGlobalLoading(false);
        }
    };

    //Click on "+ New Chat " button
    const createNewChat = async () =>
    {
        setConversationId(null);
        // Clear current chat
        setMessages([]);

        setNewChatTrigger(
          prev => prev + 1
        );
    };

    //Delete recent conversation
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

    //Rename Conversation
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

    //Add to Archive
    const archiveConversation = async (id) =>
    {
        try
        {
            setGlobalLoading(true);
            const { error } =
                await supabase
                    .from("conversations")
                    .update({
                        is_archived: true
                    })
                    .eq("id", id);

            if (error)
            {
                console.error(error);
                return;
            }

            // Clear chat if current conversation archived
            if (conversationId === id)
            {
                setConversationId(null);
                setMessages([]);
            }

            loadConversations();
        }
        finally
        {
            setGlobalLoading(false);
        }
    };

    //Export Conversation
    const exportConversation = async (conversationId, type) =>
    {
        const { data: messages } =
            await supabase
                .from("messages")
                .select("*")
                .eq("conversation_id", conversationId)
                .order(
                    "created_at",
                    {
                        ascending: true
                    }
                );

        if (!messages)
            return;

        switch(type)
        {
            case "txt":
                exportTXT(messages);
                break;

            case "md":
                exportMarkdown(messages);
                break;

            case "pdf":
                exportPDF(messages);
                break;
        }
    };

    const exportTXT = (messages) => {

        let text = "";

        messages.forEach(msg => {

            text += `${msg.role.toUpperCase()}:\n`;
            text += `${msg.content}\n\n`;

        });

        const blob =
            new Blob(
                [text],
                {
                    type: "text/plain"
                }
            );

        const url =
            URL.createObjectURL(blob);

        const a =
            document.createElement("a");

        a.href = url;

        a.download = "conversation.txt";

        a.click();

    };

    const exportMarkdown = (messages) => {

        let markdown = "";

        messages.forEach(msg => {

            markdown +=
                `## ${msg.role}\n\n`;

            markdown +=
                `${msg.content}\n\n`;

        });

        const blob =
            new Blob(
                [markdown],
                {
                    type: "text/markdown"
                }
            );

        const url =
            URL.createObjectURL(blob);

        const a =
            document.createElement("a");

        a.href = url;

        a.download = "conversation.md";

        a.click();

    };

    const exportPDF = (messages) => {

        const doc = new jsPDF();

        let y = 20;

        messages.forEach(msg => {

            doc.setFontSize(12);

            doc.text(
                `${msg.role.toUpperCase()}:`,
                10,
                y
            );

            y += 8;

            const lines =
                doc.splitTextToSize(
                    msg.content,
                    180
                );

            doc.text(
                lines,
                10,
                y
            );

            y += lines.length * 8 + 10;

        });

        doc.save(
            "conversation.pdf"
        );

    };

    //Add to Favourite
    const favoriteConversation = async (id, value) =>
    {
        try
        {
            setGlobalLoading(true);
            const { error } =
                await supabase
                    .from("conversations")
                    .update({
                        is_favorite: value
                    })
                    .eq("id", id);

            if (error) {
                console.error(error);
                return;
            }

            loadConversations();
        }
        finally{
            setGlobalLoading(false);
        }
    };

    //Open clicked conversation in Chat window
    const openConversation = async (conversationId) =>
    {
        try
        {
            setGlobalLoading(true);
            setConversationId(conversationId);

            await loadConversationMessages(conversationId);
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

    const favoriteConversations =
        conversations.filter(
            c => c.is_favorite
        );

    const normalConversations =
        conversations.filter(
            c => !c.is_favorite
        );

    //Filter conversations (search by conversation Title)
    const filteredConversations =
        normalConversations.filter(conv =>
            conv.title
                ?.toLowerCase()
                .includes(
                    searchTerm.toLowerCase()
                )
        );

    //Group Conversations (Today, Yesterday, Previous 7 Days, Older)
    const groupConversations = () => {

        const groups = {
            today: [],
            yesterday: [],
            previous7Days: [],
            older: []
        };

        filteredConversations.forEach(conv => {

            const date =
                dayjs(
                    conv.created_at
                );

            if (date.isToday())
            {
                groups.today.push(conv);
            }
            else if (date.isYesterday())
            {
                groups.yesterday.push(conv);
            }
            else if (
                dayjs().diff(
                    date,
                    "day"
                ) <= 7
            )
            {
                groups.previous7Days.push(conv);
            }
            else
            {
                groups.older.push(conv);
            }

        });

        return groups;
    };

    const grouped = groupConversations();

    const shareConversation = async (conversationId) => {
        try
        {
            setGlobalLoading(true);
            const { data, error } =
                await supabase
                    .from("shared_conversations")
                    .insert([
                        {
                            conversation_id: conversationId,
                            user_id: user.id
                        }
                    ])
                    .select()
                    .single();

            if (error) {
                console.error(error);
                return;
            }

            const url =
                `${window.location.origin}/share/${data.id}`;

            await navigator.clipboard.writeText(url);

            toast.success("Link copied!");
        }
        finally{
            setGlobalLoading(false);
        }
    };

    return (

        <div className="w-80 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 border-r border-slate-800 flex flex-col text-white">

            {/* Logo */}
            <div className="p-6 border-b border-slate-800">
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center text-2xl shadow-lg">
                        🤖
                    </div>
                    <div>
                        <h1 className="font-bold text-lg text-white">
                            General AI
                        </h1>
                        <p className="text-xs text-slate-400">
                            Your AI Workspace
                        </p>
                    </div>
                </div>
            </div>

            {mode === "archive" && (
                <>
                    {/* Back to Chat Screen */}
                    <div className="p-4">

                        <button
                            onClick={() => router.push("/")}
                            className="
                                cursor-pointer
                                w-full
                                rounded-2xl
                                py-3
                                font-semibold
                                text-white
                                bg-gradient-to-r
                                from-blue-500
                                via-purple-500
                                to-pink-500
                                hover:scale-[1.02]
                                transition
                                shadow-lg
                            "
                        >
                            ← Back to Chat
                        </button>
                    </div>

                    {/* Spacer */}
                    <div className="flex-1"></div>
                </>
            )}

            {mode === "chat" && (
                <>
                {/* New Chat */}
                <div className="p-4">

                    <button
                        onClick={createNewChat}
                        className="
                            cursor-pointer
                            w-full
                            rounded-2xl
                            py-3
                            font-semibold
                            text-white
                            bg-gradient-to-r
                            from-blue-500
                            via-purple-500
                            to-pink-500
                            hover:scale-[1.02]
                            transition
                            shadow-lg
                        "
                    >
                        ✨ New Chat
                    </button>
                    <div className="mt-3"></div>
                    <button onClick={() => router.push("/archive")} className="cursor-pointer w-full flex items-center gap-2 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white px-4 py-3 transition">
                        <ArchiveBoxIcon className="w-5 h-5 text-slate-300" />
                        <span>Archive</span>
                    </button>
                </div>

                {/* Search */}
                <div className="px-4 pb-5 relative">
                    <MagnifyingGlassIcon className="absolute left-7 top-3 w-5 h-5 text-slate-500" />
                    <input
                        type="text"
                        placeholder="Search chats..."
                        value={searchTerm}
                        onChange={(e)=>setSearchTerm(e.target.value)}
                        className="w-full rounded-2xl bg-slate-800 border border-slate-700 pl-10 pr-4 py-3 text-white placeholder:text-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 outline-none transition" />
                </div>

                {/* History */}
                <div className="flex-1 px-4 overflow-y-auto">

                    {
                        favoriteConversations.length > 0 && (

                            <div className="mb-6">

                                <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500 mb-2">
                                    <StarIcon className="w-4 h-4 text-yellow-400"/>
                                    Favorites
                                </div>

                                <div className="space-y-2-noUse">

                                    {favoriteConversations.map(conv => (

                                        <div
                                            key={conv.id}
                                            className={`relative group rounded-2xl px-4 py-3 transition-all duration-200 cursor-pointer
                                                ${
                                                    conversationId === conv.id
                                                    ? "bg-gradient-to-r from-indigo-500/25 to-purple-500/20 border border-indigo-500/30 shadow"
                                                    : "hover:bg-slate-800"
                                                }`}
                                        >
                                            <div className="flex items-center justify-between">

                                                <div className="flex items-center gap-2 flex-1 truncate" onClick={() => openConversation(conv.id)}>
                                                    <span className="truncate text-slate-100">
                                                        {conv.title}
                                                    </span>
                                                </div>

                                                {/* Three Dot Menu */}
                                                    <button onClick={(e) => {
                                                            e.stopPropagation();
                                                            setMenuOpenId(menuOpenId === conv.id ? null : conv.id );
                                                        }}
                                                        className={`cursor-pointer px-2 ${menuOpenId === conv.id ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                                                            <EllipsisVerticalIcon className="w-5 h-5 text-slate-400 hover:text-white"/>
                                                    </button>
                                            </div>
                                            {/* Popup Menu */}
                                            {menuOpenId === conv.id && (
                                                <div ref={menuOpenId === conv.id ? menuRef : null} 
                                                    className="absolute right-2 top-10 z-50 w-44 overflow-hidden rounded-2xl border border-slate-700 bg-slate-800 shadow-2xl">

                                                    <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            renameConversation(conv.id, conv.title);
                                                        }}
                                                    >
                                                        ✏️ Rename
                                                    </button>
                                                    
                                                    <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            favoriteConversation(
                                                                conv.id,
                                                                !conv.is_favorite
                                                            );
                                                        }}
                                                    >
                                                        {
                                                            conv.is_favorite
                                                            ? "⭐ Unpin"
                                                            : "⭐ Pin"
                                                        }
                                                    </button>

                                                    {/* <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            setSelectedConversation(conv);
                                                            setShowExportModal(true);
                                                        }}
                                                    >
                                                        📤 Export
                                                    </button> */}

                                                    <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            shareConversation(conv.id);
                                                        }}
                                                    >
                                                        🔗 Share
                                                    </button>

                                                    <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            archiveConversation(conv.id);
                                                        }}
                                                    >
                                                        📦 Archive
                                                    </button>

                                                    <button className="cursor-pointer w-full px-4 py-2 text-left text-red-400 hover:bg-red-500/20 transition"
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

                            </div>

                        )
                    }

                    <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500 mb-2">
                        <ClockIcon className="w-4 h-4"/>
                        Recent Chats
                    </div>

                    <div className="space-y-2-noUse">
                        {
                            [
                                {
                                    title: "Today",
                                    items: grouped.today
                                },
                                {
                                    title: "Yesterday",
                                    items: grouped.yesterday
                                },
                                {
                                    title: "Previous 7 Days",
                                    items: grouped.previous7Days
                                },
                                {
                                    title: "Older",
                                    items: grouped.older
                                }
                            ].map(section => (

                                section.items.length > 0 && (

                                    <div key={section.title} className="mb-6">
                                        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-slate-500 mb-2">
                                            {section.title}
                                        </div>

                                        <div className="space-y-2-noUse">
                                            {section.items.map(conv => (

                                                <div key={conv.id} className={`relative group rounded-2xl px-4 py-3 transition-all duration-200 cursor-pointer
                                                            ${conversationId === conv.id ? "bg-gradient-to-r from-indigo-500/25 to-purple-500/20 border border-indigo-500/30 shadow" : "hover:bg-slate-800" } `}>
                                                    
                                                    {/* Conversation Title */}
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-2 flex-1 truncate" onClick={() => openConversation(conv.id)}>
                                                            <span className="truncate text-slate-100">
                                                                {conv.title}
                                                            </span>
                                                        </div>
                                                        
                                                        {/* Three Dot Menu */}
                                                        <button onClick={(e) => {
                                                                e.stopPropagation();
                                                                setMenuOpenId(menuOpenId === conv.id ? null : conv.id );
                                                            }}
                                                            className={`cursor-pointer px-2 ${menuOpenId === conv.id ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                                                                <EllipsisVerticalIcon className="w-5 h-5 text-slate-400 hover:text-white"/>
                                                        </button>
                                                    </div>

                                                    {/* Popup Menu */}
                                                    {menuOpenId === conv.id && (
                                                        <div ref={menuOpenId === conv.id ? menuRef : null} 
                                                            className="absolute right-2 top-10 z-50 w-44 overflow-hidden rounded-2xl border border-slate-700 bg-slate-800 shadow-2xl">

                                                            <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                                onClick={() => {
                                                                    setMenuOpenId(null);
                                                                    renameConversation(conv.id, conv.title);
                                                                }}
                                                            >
                                                                ✏️ Rename
                                                            </button>
                                                            
                                                            <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                                onClick={() => {
                                                                    setMenuOpenId(null);
                                                                    favoriteConversation(
                                                                        conv.id,
                                                                        !conv.is_favorite
                                                                    );
                                                                }}
                                                            >
                                                                {
                                                                    conv.is_favorite
                                                                    ? "⭐ Unpin"
                                                                    : "⭐ Pin"
                                                                }
                                                            </button>
                                                                
                                                            {/* <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                                onClick={() => {
                                                                    setMenuOpenId(null);
                                                                    setSelectedConversation(conv);
                                                                    setShowExportModal(true);
                                                                }}
                                                            >
                                                                📤 Export
                                                            </button> */}
        
                                                            <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                                onClick={() => {
                                                                    setMenuOpenId(null);
                                                                    shareConversation(conv.id);
                                                                }}
                                                            >
                                                                🔗 Share
                                                            </button>

                                                            <button className="cursor-pointer w-full px-4 py-2 text-left text-slate-200 hover:bg-slate-700 transition"
                                                                onClick={() => {
                                                                    setMenuOpenId(null);
                                                                    archiveConversation(conv.id);
                                                                }}
                                                            >
                                                                📦 Archive
                                                            </button>

                                                            <button className="cursor-pointer w-full px-4 py-2 text-left text-red-400 hover:bg-red-500/20 transition"
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

                                    </div>

                                )

                            ))
                            }

                    </div>

                </div>
                            
                </>
            )}
            

            {/* User */}
            <div className="border-t border-slate-800 p-4">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-11 h-11 rounded-full bg-gradient-to-r rom-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center font-bold">
                        {user?.email?.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 truncate">
                        <div className="font-medium truncate text-white">
                            {user?.email}
                        </div>
                    </div>
                </div>

                <button onClick={logout}
                    className="cursor-pointer w-full rounded-2xl py-3 bg-red-500/20 text-red-300 hover:bg-red-500 hover:text-white transition">
                    🚪 Logout
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
                                className="cursor-pointer px-4 py-2 rounded-xl border border-gray-300 bg-slate-400 hover:bg-slate-500"
                            >
                                Cancel
                            </button>

                            <button
                                onClick={deleteConversation}
                                className="cursor-pointer px-4 py-2 rounded-xl bg-red-600 text-white hover:bg-red-900"
                            >
                                Delete
                            </button>

                        </div>

                    </div>

                </div>

            )}

            {/* Export Modal */}
            {
                showExportModal && (

                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">

                        <div className="bg-white rounded-2xl shadow-xl p-6 w-[400px]">

                            <h2 className="text-xl font-semibold mb-5 text-gray-800">
                                Export Conversation
                            </h2>

                            <div className="space-y-3 text-gray-600">
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <input type="radio" name="exportType" value="pdf"
                                        checked={exportType === "pdf"} onChange={(e) => setExportType(e.target.value)} />
                                    📄 PDF
                                </label>
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <input type="radio" name="exportType" value="txt" checked={exportType === "txt"}
                                        onChange={(e) => setExportType(e.target.value)} />
                                    📝 Text (.txt)
                                </label>
                                <label className="flex items-center gap-3 cursor-pointer">
                                    <input type="radio" name="exportType" value="md" checked={exportType === "md"}
                                        onChange={(e) => setExportType(e.target.value)} />
                                    📑 Markdown (.md)
                                </label>
                            </div>

                            <div className="flex justify-end gap-3 mt-8">
                                <button onClick={() => setShowExportModal(false) } className="cursor-pointer px-4 py-2 rounded-xl border border-gray-300 bg-gray-500 hover:bg-gray-900">
                                    Cancel
                                </button>
                                <button className="cursor-pointer px-5 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700"
                                    onClick={() => {
                                        exportConversation(
                                            selectedConversation.id,
                                            exportType
                                        );
                                        setShowExportModal(false);
                                    }}                            
                                >
                                    Export
                                </button>

                            </div>

                        </div>

                    </div>

                )
            }

        </div>
    );
}