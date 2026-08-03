"use client";

import { useEffect, useState, useRef } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useConversation } from "@/context/ConversationProvider";
import { useAuth } from "@/context/AuthProvider";
import { useLoading } from "@/context/LoadingContext"

import jsPDF from "jspdf";

import { PlusIcon, EllipsisVerticalIcon, MagnifyingGlassIcon, ClockIcon } from "@heroicons/react/24/outline";
import { ArchiveBoxIcon, StarIcon  } from "@heroicons/react/24/solid";

import dayjs from "dayjs";
import isToday from "dayjs/plugin/isToday";
import isYesterday from "dayjs/plugin/isYesterday";

dayjs.extend(isToday);
dayjs.extend(isYesterday);

export default function Sidebar({ mode = "chat" }) {
    const { setGlobalLoading } = useLoading();

    //Maintain sidebar open or close on next screen load
    const [collapsed, setCollapsed] = useState(() => {
        if (typeof window === "undefined") return false;
        return localStorage.getItem("sidebarCollapsed") === "true";
    });
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

    useEffect(() => 
    {
        localStorage.setItem(
            "sidebarCollapsed",
            collapsed
        );
    }, [collapsed]);

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

        <div className={`
        ${collapsed ? "w-20" : "w-[320px]"}
        bg-[#0B1324]
        text-white
        flex
        flex-col
        transition-all
        duration-300
        relative
    `}>

            <button
                    onClick={() => setCollapsed(!collapsed)}
                    className={`absolute right-0 top-8 h-8 w-8 rounded-xl bg-white border flex items-center justify-center text-gray-400 z-50 hover:scale-105
                        ${collapsed ? "opacity-0 hover:opacity-100" : "opacity-100"}
                    `}
                >
                    {collapsed ? <span title="Expand sidebar">▶</span> : <span title="Collapse sidebar">◀</span>}
                </button>
            {/* Header */}

            <div className="border-b border-white/10 px-3 py-6">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg text-2xl">
                            🤖
                        </div>
                        {!collapsed && (
                            <div>
                                <h1 className="text-xl font-bold tracking-wide">
                                    General AI
                                </h1>

                                <p className="text-sm text-gray-400">
                                    Your AI Workspace
                                </p>
                            </div>
                        )}

                    </div>

                </div>

            </div>

            {mode === "archive" && (

                <>

                    <div className="p-6">

                        <button title="Back to chat"
                            onClick={() => router.push("/")}
                            className="
                                cursor-pointer
                                w-full
                                h-12
                                rounded-xl
                                bg-indigo-600
                                hover:bg-indigo-700
                                font-semibold
                                transition
                                duration-200
                            "
                        >
                            ← {!collapsed && "Back to Chat"}
                        </button>

                    </div>

                    <div className="flex-1" />

                </>

            )}

            {mode === "chat" && (
                <>
                {/* New Chat */}
                <div className="px-5 pt-5 space-y-3">

                    <button
                        title="New Chat"
                        onClick={createNewChat}
                        className="
                            cursor-pointer
                            w-full
                            h-12
                            rounded-xl
                            bg-indigo-600
                            hover:bg-indigo-700
                            font-semibold
                            transition-all
                            duration-200
                            shadow-lg
                        "
                    >
                        <div className={`flex items-center ${collapsed ? "justify-center" : "justify-center gap-2"}`}>
                            <PlusIcon className="w-5 h-5"/>
                            {!collapsed && <span>New Chat</span>}
                        </div>
                    </button>
                    <div className="mt-3"></div>
                    <button title="View Archive"
                        onClick={() => router.push("/archive")}
                        className="
                            cursor-pointer
                            w-full
                            h-12
                            rounded-xl
                            border
                            border-white/10
                            bg-white/5
                            hover:bg-white/10
                            transition-all
                            duration-200
                        "
                    >
                        <div className={`flex items-center ${collapsed ? "justify-center" : "justify-center gap-2"}`}>
                            <ArchiveBoxIcon className="w-5 h-5"/>
                            {!collapsed && <span>Archive</span>}
                        </div>
                    </button>
                </div>

                {/* Search */}
                {!collapsed && (
                <div className="px-5 py-5">

                    <div className="relative">

                        <MagnifyingGlassIcon
                            className="
                                absolute
                                left-4
                                top-3.5
                                w-5
                                h-5
                                text-gray-400
                            "
                        />

                        <input
                            type="text"
                            placeholder="Search conversations..."
                            value={searchTerm}
                            onChange={(e)=>setSearchTerm(e.target.value)}
                            className="
                                w-full
                                h-12
                                rounded-xl
                                bg-white/5
                                border
                                border-white/10
                                pl-11
                                pr-4
                                text-sm
                                text-white
                                placeholder:text-gray-500
                                focus:border-indigo-500
                                focus:ring-2
                                focus:ring-indigo-500/20
                                outline-none
                            "
                        />

                    </div>

                </div>
                )}

                {/* History */}
                <div className="flex-1 overflow-y-auto px-5 pb-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-600 scrollbar-track-transparent">

                    {!collapsed &&
                        favoriteConversations.length > 0 && (

                            <div className="mb-8">

                                <div className="flex items-center justify-between mb-4">

                                    <div className="flex items-center gap-2">

                                        <StarIcon className="w-4 h-4 text-amber-400"/>                                        
                                        <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">
                                            Favorites
                                        </span>
                                    </div>

                                </div>

                                <div className="space-y-2">

                                    {favoriteConversations.map(conv => (

                                        <div
                                            key={conv.id}
                                            className={`relative group rounded-xl px-4 py-3 transition-all duration-200 cursor-pointer
                                                ${
                                                    conversationId === conv.id
                                                    ? "bg-indigo-600 border-indigo-500 shadow-lg"
                                                    : "bg-white/5 border-transparent hover:bg-white/10"
                                                }`}
                                        >
                                            <div className="flex items-center justify-between">

                                                <div className="flex items-center gap-2 flex-1 truncate" onClick={() => openConversation(conv.id)}>
                                                    {!collapsed ? (
                                                        <span className="truncate text-sm font-medium">
                                                            {conv.title}
                                                        </span>
                                                    ) : (
                                                        <div className="w-3 h-3 rounded-full bg-indigo-400"></div>
                                                    )}
                                                </div>

                                                {/* Three Dot Menu */}
                                                {!collapsed && (
                                                    <button onClick={(e) => {
                                                            e.stopPropagation();
                                                            setMenuOpenId(menuOpenId === conv.id ? null : conv.id );
                                                        }}
                                                        className={`cursor-pointer rounded-lg transition ${menuOpenId === conv.id ? "opacity-100 bg-white/10" : "opacity-0 group-hover:opacity-100"}`}>
                                                            <EllipsisVerticalIcon className="w-5 h-5 text-slate-400 hover:text-white"/>
                                                    </button>
                                                )}
                                            </div>
                                            {/* Popup Menu */}
                                            {!collapsed && menuOpenId === conv.id && (
                                                <div ref={menuOpenId === conv.id ? menuRef : null} 
                                                    className="absolute right-0 top-12 w-48 rounded-xl bg-white shadow-2xl overflow-hidden z-50">

                                                    <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            renameConversation(conv.id, conv.title);
                                                        }}
                                                    >
                                                        ✏️ Rename
                                                    </button>
                                                    
                                                    <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
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

                                                    {/* <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            setSelectedConversation(conv);
                                                            setShowExportModal(true);
                                                        }}
                                                    >
                                                        📤 Export
                                                    </button> */}

                                                    <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
                                                        onClick={() => {
                                                            setMenuOpenId(null);
                                                            shareConversation(conv.id);
                                                        }}
                                                    >
                                                        🔗 Share
                                                    </button>

                                                    <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
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
                    
                    {!collapsed && (
                    <>
                        <div className="flex items-center justify-between mb-5">

                            <div className="flex items-center gap-2">

                                <ClockIcon className="w-4 h-4 text-gray-400"/>
                                {!collapsed && (
                                    <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">
                                        Recent Chats
                                    </span>
                                )}
                            </div>

                        </div>
                    
                    
                        <div className="space-y-2">
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

                                        <div key={section.title} className="mb-8">
                                            <div className="mb-3">                                                
                                                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-500">
                                                    {section.title}
                                                </span>                                                
                                            </div>

                                            <div className="space-y-2">
                                                {section.items.map(conv => (

                                                    <div
                                                        key={conv.id}
                                                        className={`relative group rounded-xl px-4 py-3 transition-all duration-200 cursor-pointer
                                                            ${
                                                                conversationId === conv.id
                                                                ? "bg-indigo-600 border-indigo-500 shadow-lg"
                                                                : "bg-white/5 border-transparent hover:bg-white/10"
                                                            }`}
                                                    >
                                                        <div className="flex items-center justify-between">

                                                            <div className="flex items-center gap-2 flex-1 truncate" onClick={() => openConversation(conv.id)}>
                                                                {!collapsed ? (
                                                                    <span className="truncate text-sm font-medium">
                                                                        {conv.title}
                                                                    </span>
                                                                ) : (
                                                                    <div className="w-3 h-3 rounded-full bg-indigo-400"></div>
                                                                )}
                                                            </div>
                                                            
                                                            {/* Three Dot Menu */}
                                                            {!collapsed && (
                                                                <button onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        setMenuOpenId(menuOpenId === conv.id ? null : conv.id );
                                                                    }}
                                                                    className={`cursor-pointer px-2 ${menuOpenId === conv.id ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                                                                        <EllipsisVerticalIcon className="w-5 h-5 text-slate-400 hover:text-white"/>
                                                                </button>
                                                            )}
                                                        </div>

                                                        {/* Popup Menu */}
                                                        {!collapsed && menuOpenId === conv.id && (
                                                            <div ref={menuOpenId === conv.id ? menuRef : null} 
                                                                className="absolute right-0 top-12 w-48 rounded-xl bg-white shadow-2xl overflow-hidden z-50">

                                                                <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
                                                                    onClick={() => {
                                                                        setMenuOpenId(null);
                                                                        renameConversation(conv.id, conv.title);
                                                                    }}
                                                                >
                                                                    ✏️ Rename
                                                                </button>
                                                                
                                                                <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
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
                                                                    
                                                                {/* <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
                                                                    onClick={() => {
                                                                        setMenuOpenId(null);
                                                                        setSelectedConversation(conv);
                                                                        setShowExportModal(true);
                                                                    }}
                                                                >
                                                                    📤 Export
                                                                </button> */}
            
                                                                <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
                                                                    onClick={() => {
                                                                        setMenuOpenId(null);
                                                                        shareConversation(conv.id);
                                                                    }}
                                                                >
                                                                    🔗 Share
                                                                </button>

                                                                <button className="cursor-pointer w-full px-4 py-3 text-left text-gray-700 hover:bg-gray-100 transition text-sm"
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
                    </>
                    )}

                    {/* Empty State */}
                    {!collapsed && conversations.length === 0 && (

                        <div className="flex flex-col items-center justify-center py-16 text-center">

                            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                                <PlusIcon className="w-8 h-8 text-gray-500" />
                            </div>

                            <h3 className="text-white font-semibold">
                                No conversations yet
                            </h3>

                            <p className="text-gray-400 text-sm mt-2">
                                Click "New Chat" to start your first conversation.
                            </p>

                        </div>

                    )}

                </div>
                            
                </>
            )}
            

            {/* User */}
            
            <div className="border-t border-white/10 p-5">

                <div
                    className="
                        bg-white/5
                        rounded-2xl
                        p-4
                        border
                        border-white/10
                    "
                >

                    <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>

                        <div
                            className={`
                                w-12
                                h-12                                
                                flex
                                items-center
                                justify-center
                                text-lg
                                font-bold
                                ${!collapsed ? "rounded-full bg-indigo-600" : "" }
                            `}
                        >
                            {user?.email?.charAt(0).toUpperCase()}
                        </div>

                        {!collapsed && (
                            <div className="flex-1 min-w-0">

                                {/* <div className="font-semibold truncate">
                                    {user?.user_metadata?.full_name || "User"}
                                </div> */}

                                <div className="text-sm text-gray-400 truncate">
                                    {user?.email}
                                </div>

                            </div>
                        )}
                    </div>

                    <button title="Logout"
                        onClick={logout}
                        className={`cursor-pointer mt-4 w-full h-11 text-red-300 flex items-center justify-center transition duration-200
                            ${!collapsed ? "rounded-xl border border-red-500/40 hover:bg-red-600 hover:text-white" : "" }
                        `}
                    ><span title="Logout" className="leading-none">🚪{collapsed ? "" : " Logout"}</span>
                    </button>

                </div>

            </div>

            {/* Delete Conversation Modal */}
            {deleteModalOpen && (

            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">

                <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md p-8">

                    <h2 className="text-2xl font-bold text-gray-900">
                        Delete Conversation
                    </h2>

                    <p className="mt-3 text-gray-500 leading-7">
                        This conversation will be permanently deleted.
                        This action cannot be undone.
                    </p>

                    <div className="flex justify-end gap-3 mt-8">

                        <button
                            onClick={()=>{
                                setDeleteModalOpen(false);
                                setConversationToDelete(null);
                            }}
                            className="cursor-pointer rounded-xl border px-5 py-3 hover:bg-slate-100 text-black"
                        >
                            Cancel
                        </button>

                        <button
                            onClick={deleteConversation}
                            className="
                                cursor-pointer
                                px-5
                                py-3
                                rounded-xl
                                bg-red-600
                                text-white
                                hover:bg-red-700
                            "
                        >
                            Delete
                        </button>

                    </div>

                </div>

            </div>

            )}

            {/* Export Modal */}
            {showExportModal && (

            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">

                <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md p-8">

                    <h2 className="text-2xl font-bold text-gray-900">
                        Export Conversation
                    </h2>

                    <p className="text-gray-500 mt-2">
                        Choose your preferred export format.
                    </p>

                    <div className="space-y-4 mt-8">

                        <label className="flex items-center gap-3 rounded-xl border p-4 cursor-pointer hover:bg-gray-50">

                            <input
                                type="radio"
                                value="pdf"
                                checked={exportType==="pdf"}
                                onChange={(e)=>setExportType(e.target.value)}
                            />

                            <span className="font-medium">
                                PDF Document
                            </span>

                        </label>

                        <label className="flex items-center gap-3 rounded-xl border p-4 cursor-pointer hover:bg-gray-50">

                            <input
                                type="radio"
                                value="txt"
                                checked={exportType==="txt"}
                                onChange={(e)=>setExportType(e.target.value)}
                            />

                            <span className="font-medium">
                                Text File (.txt)
                            </span>

                        </label>

                        <label className="flex items-center gap-3 rounded-xl border p-4 cursor-pointer hover:bg-gray-50">

                            <input
                                type="radio"
                                value="md"
                                checked={exportType==="md"}
                                onChange={(e)=>setExportType(e.target.value)}
                            />

                            <span className="font-medium">
                                Markdown (.md)
                            </span>

                        </label>

                    </div>

                    <div className="flex justify-end gap-3 mt-8">

                        <button
                            onClick={()=>setShowExportModal(false)}
                            className="cursor-pointer rounded-xl border px-5 py-3 hover:bg-slate-100 text-black"
                        >
                            Cancel
                        </button>

                        <button
                            onClick={()=>{
                                exportConversation(
                                    selectedConversation.id,
                                    exportType
                                );
                                setShowExportModal(false);
                            }}
                            className="
                                cursor-pointer
                                px-5
                                py-3
                                rounded-xl
                                bg-[#0B1324]
                                text-white
                                hover:bg-black
                            "
                        >
                            Export
                        </button>

                    </div>

                </div>

            </div>

            )}

        </div>
    );
}