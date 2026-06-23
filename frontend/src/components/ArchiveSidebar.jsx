"use client";

import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/context/AuthProvider";
import { useLoading } from "@/context/LoadingContext"

export default function ArchiveSidebar() {

    const router = useRouter();

    const { user } = useAuth();

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

            <div className="p-4">

                <button onClick={() => router.push("/")} className="cursor-pointer text-left w-full bg-slate-800 hover:bg-slate-700 rounded-xl py-3 px-3">
                    ← Back to Chat Screen
                </button>
            </div>
            {/* Spacer */}
            <div className="flex-1"></div>

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

        </div>
    );
}