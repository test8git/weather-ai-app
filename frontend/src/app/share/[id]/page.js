"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function SharedPage() {

    const params = useParams();
    const [messages, setMessages] = useState([]);

    useEffect(() => {
        if (params?.id) {
            loadConversation();
        }
    }, [params]);

    const loadConversation = async () => {

        // find shared row
        const { data: shared } =
            await supabase
                .from("shared_conversations")
                .select("*")
                .eq("id", params.id)
                .single();

        if (!shared)
            return;

        // load messages
        const { data } =
            await supabase
                .from("messages")
                .select("*")
                .eq(
                    "conversation_id",
                    shared.conversation_id
                )
                .order(
                    "created_at",
                    {
                        ascending: true
                    }
                );

        setMessages(data || []);
    };

    return (
        <div className="max-w-4xl mx-auto p-8">
            <h1 className="text-3xl font-bold mb-8">
                Shared Conversation
            </h1>
            {
                messages.map(msg => (
                    <div key={msg.id}className="mb-6">
                        <b>
                            {msg.role}
                        </b>

                        <div>
                            {msg.content}
                        </div>
                    </div>
                ))
            }
        </div>
    );
}