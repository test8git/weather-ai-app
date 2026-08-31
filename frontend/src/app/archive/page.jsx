"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/context/AuthProvider";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useLoading } from "@/context/LoadingContext"
// import ArchiveSidebar from "@/components/ArchiveSidebar";
import Sidebar from "@/components/Sidebar";

export default function ArchivePage()
{
    const { user } = useAuth();
    const [error, setError] = useState("");
    const [conversations, setConversations] = useState([]);
    const { setGlobalLoading } = useLoading();
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [conversationToDelete, setConversationToDelete] = useState(null);

    const router = useRouter();

    useEffect(() => 
    {

        if (user)
        {
            loadArchived();
        }

    }, [user]);

    const loadArchived = async () =>
    {
        try{
            setGlobalLoading(true);
        
            const { data, error } =
                await supabase
                    .from("conversations")
                    .select("*")
                    .eq("user_id", user.id)
                    .eq("is_archived", true)
                    .order(
                        "created_at",
                        {
                            ascending: false
                        }
                    );

            if (error)
            {
                console.log(error);
                return;
            }

            setConversations(data || []);
        }
        finally{
            setGlobalLoading(false);
        }
    };

    //Delete recent conversation
    const deleteConversation = async (id) =>
    {
        if (!conversationToDelete)
            return;

        try
        {
            setGlobalLoading(true);
            const { error } = await supabase.from("conversations").delete().eq("id", conversationToDelete);

            if (error)
            {
                console.log(error);

                return;
            }

            setDeleteModalOpen(false);
            setConversationToDelete(null);
            loadArchived();
        }
        finally
        {
            setGlobalLoading(false);
        }
    };

    //Restore Conversation
    const restoreConversation = async (id) =>
    {
        try{
            setGlobalLoading(true);
            await supabase
                .from("conversations")
                .update({
                    is_archived: false
                })
                .eq("id", id);

            loadArchived();
        }
        finally{
            setGlobalLoading(false);
        }
    };

    //Empty Archive
    const emptyArchive = async () =>
    {
        try{
            setGlobalLoading(true);
            const { error } =
                await supabase
                    .from("conversations")
                    .delete()
                    .eq("user_id", user.id)
                    .eq("is_archived", true);

            if (error) {
                console.log(error);
                alert("Failed to empty archive");
                return;
            }

            setConversations([]);

            setShowDeleteAllModal(false);
        }
        finally{
            setGlobalLoading(false);
        }
    };

    return (
        <ProtectedRoute>
              <div className="flex h-screen overflow-hidden">
                <Sidebar mode="archive" collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
                <div className="flex-1 bg-slate-100 p-4 min-w-0">
                    {error && (
                    <div className="mb-3">
                        <p className="text-red-500">
                        {error}
                        </p>
                    </div>
                    )}
                    <div className="font-[Inter] h-full bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden flex flex-col">
                        <div className="border-b border-slate-200 bg-white px-8 py-6">

                            <div className="flex items-center justify-between">

                                <div className="flex items-center gap-4">

                                    <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white flex items-center justify-center shadow-lg text-2xl">
                                        📦
                                    </div>

                                    <div>

                                        <h1 className="text-3xl font-bold text-slate-800">
                                            Archive
                                        </h1>

                                        <p className="text-slate-500 mt-1">
                                            View and restore archived conversations
                                        </p>

                                    </div>

                                </div>

                                <div className="flex items-center gap-4">

                                    <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600">
                                        {conversations.length} Conversations
                                    </div>

                                    {conversations.length > 0 && (

                                        <button
                                            onClick={() => setShowDeleteAllModal(true)}
                                            className="cursor-pointer rounded-xl bg-red-500 px-5 py-3 text-white hover:bg-red-600 transition shadow-md"
                                        >
                                            Empty Archive
                                        </button>

                                    )}

                                </div>

                            </div>

                        </div>
                        {
                            conversations.length === 0 ?
                            (
                                <div className="flex flex-1 items-center justify-center bg-slate-50">

                                    <div className="text-center max-w-md">

                                        <div className="mx-auto h-28 w-28 rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 text-white flex items-center justify-center text-5xl shadow-xl">
                                            📦
                                        </div>

                                        <h2 className="mt-8 text-3xl font-bold text-slate-800">
                                            Nothing Archived Yet
                                        </h2>

                                        <p className="mt-4 text-slate-500 leading-7">
                                            Archived conversations will appear here. Restore them anytime with one click.
                                        </p>

                                        <button
                                            onClick={() => router.push("/")}
                                            className="
                                                mt-8
                                                cursor-pointer
                                                rounded-2xl
                                                bg-gradient-to-r
                                                from-violet-600
                                                to-indigo-600
                                                px-7
                                                py-3.5
                                                text-white
                                                shadow-lg
                                                hover:scale-105
                                                transition
                                            "
                                        >
                                            Back to Chat
                                        </button>

                                    </div>

                                </div>

                            )
                            :
                            (
                                <div className="flex-1 overflow-y-auto p-8 bg-slate-50">

                                    <div className="space-y-5">

                                        {conversations.map((conv) => (

                                            <div
                                                key={conv.id}
                                                className="
                                                    group
                                                    rounded-3xl
                                                    bg-white
                                                    border
                                                    border-slate-200
                                                    p-6
                                                    shadow-sm
                                                    hover:shadow-xl
                                                    hover:border-violet-300
                                                    transition-all
                                                    duration-300
                                                "
                                            >

                                                <div className="flex justify-between">

                                                    <div className="flex-1">

                                                        <h3 className="font-semibold text-lg text-slate-800">
                                                            {conv.title}
                                                        </h3>

                                                        <p className="text-sm text-slate-500 mt-2">
                                                            Archived conversation
                                                        </p>

                                                    </div>

                                                    <div className="flex gap-3">

                                                        <button
                                                            onClick={() => restoreConversation(conv.id)}
                                                            className="
                                                                cursor-pointer
                                                                rounded-xl
                                                                bg-gradient-to-r
                                                                from-violet-600
                                                                to-indigo-600
                                                                px-5
                                                                py-2.5
                                                                text-white
                                                                hover:scale-105
                                                                transition
                                                            "
                                                        >
                                                            Restore
                                                        </button>

                                                        <button
                                                            onClick={() => {
                                                                setConversationToDelete(conv.id);
                                                                setDeleteModalOpen(true);
                                                            }}
                                                            className="
                                                                cursor-pointer
                                                                rounded-xl
                                                                border
                                                                border-red-300
                                                                px-5
                                                                py-2.5
                                                                text-red-600
                                                                hover:bg-red-50
                                                            "
                                                        >
                                                            Delete
                                                        </button>

                                                    </div>

                                                </div>

                                            </div>

                                        ))}

                                    </div>

                                </div>
                            )
                        }
                    </div>
                </div>
                {
                showDeleteAllModal && (

                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">

                    <div className="w-[420px] rounded-3xl bg-white p-8 shadow-2xl">

                        <div className="text-center">

                            <div className="mx-auto h-16 w-16 rounded-full bg-red-100 flex items-center justify-center text-3xl">
                                🗑
                            </div>

                            <h2 className="mt-5 text-2xl font-bold">
                                Empty Archive?
                            </h2>

                            <p className="mt-3 text-slate-500">
                                This will permanently delete every archived conversation.
                            </p>

                        </div>

                        <div className="mt-8 flex justify-end gap-3">

                            <button
                                onClick={() => setShowDeleteAllModal(false)}
                                className="cursor-pointer rounded-xl border px-5 py-3 hover:bg-slate-100"
                            >
                                Cancel
                            </button>

                            <button
                                onClick={emptyArchive}
                                className="cursor-pointer rounded-xl bg-red-500 px-5 py-3 text-white hover:bg-red-600"
                            >
                                Delete All
                            </button>

                        </div>

                    </div>

                </div>

                )
                }
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
                                className="cursor-pointer rounded-xl border px-5 py-3 hover:bg-slate-100"
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
            </div>
        </ProtectedRoute>
    );
}