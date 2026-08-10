"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import toast from "react-hot-toast";

export default function ConnectZapierModal({
    open,
    onClose,
    onConnected,
    profile
})
{
    const [mcpUrl, setMcpUrl] = useState("");
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (open)
        {
            setMcpUrl(profile?.mcp_url || "");
        }
    }, [open, profile]);

    if (!open) return null;

    function closeModal() {
        //setMcpUrl("");
        onClose();
    }

    async function connectZapier()
    {
        if (!mcpUrl.trim())
        {
            toast.error("Please enter MCP URL");
            return;
        }

        setLoading(true);

        try
        {
            const { data: { session }} = await supabase.auth.getSession();

            const res = await fetch(
                process.env.NEXT_PUBLIC_API_URL + "/api/mcp/connect",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",

                        Authorization:
                            `Bearer ${session.access_token}`
                    },

                    body: JSON.stringify({
                        mcp_url: mcpUrl
                    })
                }
            );

            const data = await res.json();

            if(data.status)
            {
                await onConnected?.();
                closeModal();
            }
            else
            {
                toast.error(data.message);
            }
        }
        catch(err)
        {
            toast.error(err.message);
        }

        setLoading(false);
    }

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">

            <div className="bg-white rounded-2xl w-[600px] p-8 border border-white/10 text-gray-900">

                <h2 className="text-2xl font-bold mb-5">
                    Connect Zapier MCP
                </h2>

                <p className="text-gray-400 mb-5">
                    Paste your Zapier MCP URL.
                </p>

                <input
                    value={mcpUrl}
                    onChange={(e)=>setMcpUrl(e.target.value)}
                    placeholder="https://mcp.zapier.com/api/..."
                    className="w-full h-12 border rounded-xl px-4 outline-none"
                />

                <div className="mt-8 flex justify-end gap-4">

                    <button
                        onClick={closeModal}
                        className="cursor-pointer rounded-xl border px-5 py-3 hover:bg-slate-100 text-black"
                    >
                        Cancel
                    </button>

                    <button
                        onClick={connectZapier}
                        disabled={loading}
                        className="cursor-pointer px-5 py-3 rounded-xl text-white bg-indigo-600"
                    >
                        {loading ? "Connecting..." : "Connect"}
                    </button>

                </div>

            </div>

        </div>
    );
}