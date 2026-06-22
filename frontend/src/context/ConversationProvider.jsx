"use client";

import {createContext,useContext,useState} from "react";

const ConversationContext = createContext();

export function ConversationProvider({ children })
{
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newChatTrigger, setNewChatTrigger] = useState(0);
  const [conversations, setConversations] = useState([]);

  return (
    <ConversationContext.Provider value={{ 
        conversationId, setConversationId, 
        messages, setMessages, 
        newChatTrigger, setNewChatTrigger, 
        conversations, setConversations
}}>
      {children}
    </ConversationContext.Provider>
  );
}

export const useConversation = () =>
  useContext(ConversationContext);