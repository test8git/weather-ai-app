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
    const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);

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
                console.error(error);
                return;
            }

            setConversations(data || []);
        }
        finally{
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
                console.error(error);
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
              <div className="flex h-screen">
                <Sidebar mode="archive" />
                <div className="flex-1 bg-slate-100 p-4">
                    {error && (
                    <div className="mb-3">
                        <p className="text-red-500">
                        {error}
                        </p>
                    </div>
                    )}
                    <div className="font-[Inter] h-full bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden flex flex-col">
                        <div className="border-b border-slate-200 px-8 py-6 flex items-center justify-between">

                            <div>

                                <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
                                    📦 Archived Conversations
                                </h1>

                                <p className="text-slate-500 mt-2">
                                    {conversations.length} archived conversations
                                </p>

                            </div>

                            {conversations.length > 0 && (

                                <button
                                    onClick={() => setShowDeleteAllModal(true)}
                                    className="cursor-pointer flex items-center gap-2 rounded-xl bg-red-500 px-5 py-3 text-white hover:bg-red-600 transition shadow"
                                >
                                    🗑 Empty Archive
                                </button>

                            )}

                        </div>
                        {
                            conversations.length === 0 ?
                            (
                                <div className="flex flex-1 items-center justify-center">

                                    <div className="text-center">

                                        <div className="text-7xl mb-6">
                                            📦
                                        </div>

                                        <h2 className="text-3xl font-bold text-slate-700">
                                            Archive is empty
                                        </h2>

                                        <p className="mt-3 text-slate-500">
                                            Conversations you archive will appear here.
                                        </p>

                                        <button
                                            onClick={()=>router.push("/")}
                                            className="
                                                cursor-pointer
                                                mt-8
                                                rounded-xl
                                                bg-gradient-to-r
                                                from-blue-500
                                                via-purple-500
                                                to-pink-500
                                                px-6
                                                py-3
                                                text-white
                                                font-semibold
                                            "
                                        >
                                            ← Back to Chat
                                        </button>

                                    </div>

                                </div>

                            )
                            :
                            (
                                conversations.map((conv) => (
                                    <div key={conv.id} className="bg-white shadow rounded-xl p-4 mb-3 flex justify-between">
                                        <div>
                                            {conv.title}
                                        </div>
                                        <button onClick={() => restoreConversation(conv.id)} className="cursor-pointer text-blue-500">Restore</button>
                                    </div>
                                ))
                            )
                        }
                    </div>
                </div>
                {
                showDeleteAllModal && (

                <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">

                    <div className="bg-white rounded-2xl shadow-xl p-6 w-96">

                        <h2 className="text-xl font-semibold mb-4">
                            Empty Archive
                        </h2>

                        <p className="text-gray-600 mb-6">
                            Are you sure you want to permanently delete all archived conversations?
                        </p>

                        <div className="flex justify-end gap-3">

                            <button
                                onClick={() => setShowDeleteAllModal(false)}
                                className="cursor-pointer px-4 py-2 border rounded-xl"
                            >
                                Cancel
                            </button>

                            <button
                                onClick={emptyArchive}
                                className="cursor-pointer px-4 py-2 bg-red-500 text-white rounded-xl hover:bg-red-600"
                            >
                                Delete All
                            </button>

                        </div>

                    </div>

                </div>

                )
                }
            </div>
        </ProtectedRoute>
    );
}