"use client";

import {createContext,useContext,useState} from "react";
import { supabase } from "@/lib/supabase";

const ConversationContext = createContext();

export function ConversationProvider({ children })
{
  const [conversationId, setConversationId] = useState(null);
  const [responseBranches, setResponseBranches] = useState({});
  const [messages, setMessages] = useState([]);
  const [newChatTrigger, setNewChatTrigger] = useState(0);
  const [conversations, setConversations] = useState([]);

  const loadConversationMessages = async (conversationId) => {
        const { data, error } =
            await supabase
                .from("messages")
                .select("*")
                .eq("conversation_id", conversationId)
                .order("created_at", {
                    ascending: true
                });

        if (error) {
            console.log(error);
            return;
        }

        //Store latest response
        const latestAssistantMap = {};
        data.forEach(msg =>
        {
            if (msg.role === "assistant" && msg.parent_user_message_id)
            {
                const parentId = msg.parent_user_message_id;

                if (!latestAssistantMap[parentId] || msg.response_version > latestAssistantMap[parentId].response_version)
                {
                    latestAssistantMap[parentId] = msg;
                }
            }
        });

        //Store user question & latest response to display
        const finalMessages = [];
        data.forEach(msg =>
        {
            if (msg.role === "user")
            {
                finalMessages.push(msg);

                if (latestAssistantMap[msg.id])
                {
                    finalMessages.push(latestAssistantMap[msg.id]);
                }
            }
        });

        /* OUTPUT
        {
          U1:
          {
              current: 1,
              versions:[A1, A2, A3]
          }
        }
        */
        const branches = {};
        data.forEach(msg =>
        {
            if (msg.role === "assistant" && msg.parent_user_message_id)
            {
                const parentId = msg.parent_user_message_id;

                if (!branches[parentId])
                {
                    branches[parentId] =
                    {
                        current: 1,
                        versions: []
                    };
                }

                branches[parentId].versions.push(msg);
            }
        });

        /* OUTPUT
        {
          U1:
          {
              current: 3,
              versions:[A1, A2, A3]
          }
        }
        */
        Object.keys(branches).forEach(parentId =>
        {
            const total = branches[parentId].versions.length;
            branches[parentId].current = total;
        });

        setResponseBranches(branches);
        setMessages(finalMessages);
    };

  return (
    <ConversationContext.Provider value={{ 
        conversationId, setConversationId, 
        messages, setMessages, 
        newChatTrigger, setNewChatTrigger, 
        conversations, setConversations,
        responseBranches, setResponseBranches,
        loadConversationMessages
}}>
      {children}
    </ConversationContext.Provider>
  );
}

export const useConversation = () =>
  useContext(ConversationContext);