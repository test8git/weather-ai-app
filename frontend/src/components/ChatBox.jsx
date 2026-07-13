"use client";

import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useConversation } from "@/context/ConversationProvider";
import { useEffect, useRef, useState } from "react";
import { useLoading } from "@/context/LoadingContext"
import CustomChart from "@/components/CustomChart";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import "@fontsource/inter";
import {Prism as SyntaxHighlighter} from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { HandThumbUpIcon,HandThumbDownIcon, PaperClipIcon } from "@heroicons/react/24/outline";
import {HandThumbUpIcon as HandThumbUpSolid, HandThumbDownIcon as HandThumbDownSolid } from "@heroicons/react/24/solid";
import "katex/dist/katex.min.css";

export default function ChatBox() {

  const router = useRouter();

  const [user, setUser] = useState(null);
  const [question, setQuestion] = useState("");
  const [isLoadingLocal, setIsLoadingLocal] = useState(false);
  const { setGlobalLoading } = useLoading();
  const { messages, setMessages, conversationId, setConversationId, newChatTrigger, conversations, setConversations, responseBranches, setResponseBranches} = useConversation();
  const [status, setStatus] = useState("");
  const [steps, setSteps] = useState([]);
  const messagesEndRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const inputRef = useRef(null);

  const [speechSupported, setSpeechSupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  //Speak Response
  const [speakingMessageId, setSpeakingMessageId] = useState(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const speakRef = useRef(null);


  //Stop Generation
  const controllerRef = useRef(null);
  const [isGenerating, setIsGenerating] = useState(false);

  //Edit Prompt
  const [editingIndex, setEditingIndex] = useState(null);
  const [editingText, setEditingText] = useState("");

  const [feedbackModalOpen, setFeedbackModalOpen] = useState(false);
  const [selectedMessageId, setSelectedMessageId] = useState(null);
  const [feedbackReason, setFeedbackReason] = useState("");
  const [feedbackComment, setFeedbackComment] = useState("");

  const session_id = user?.id || "";

  useEffect(() => {

      const loadUser = async () => {

          const {data: { user }} = await supabase.auth.getUser();

          if (!user) {
              router.push("/login");
              return;
          }

          setUser(user);

      };

      loadUser();

  }, [router]);
  
  //let totalDuration = 0;


  //Check for Clientside Speech supported
  useEffect(() => {
    setSpeechSupported(
      !!(
        window.SpeechRecognition ||
        window.webkitSpeechRecognition
      )
    );
  }, []);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
        behavior: "smooth"
    });    
  }, [messages]);

  //Drag event registration
  useEffect(() => {

      const handleDragEnd = () => {
          setIsDragging(false);
      };

      window.addEventListener("dragend", handleDragEnd);

      return () => {
          window.removeEventListener("dragend", handleDragEnd);
      };

  }, []);

  useEffect(() => {
    setQuestion("");
  }, [newChatTrigger]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [newChatTrigger]);

  const handleSearchKeyDown = (e) => {
    if (e.key === "Enter") {
      askAI();
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];

    if (file) {
      setSelectedFile(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();

    setIsDragging(false);

    if (e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
     e.preventDefault();

    if (!isDragging) {
      setIsDragging(true);
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const isAudioFile = (file) => {
    return file?.type?.startsWith("audio/");
  };

  const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const askAI = async (voiceQuestion = null, parentUserMessageId = null, responseVersion = 1, replaceAssistantId = null) => {
    
    let assistantText = "";
    let responseSaved = false;
    let currentConversationId = conversationId;

    try 
    {
      if (!user) {
          alert("Please login first");
          return;
      }
        const actualQuestion = voiceQuestion || question;

        if (!selectedModel.trim()) {
            alert("Please select AI modal");
            return;
        }
        if (!actualQuestion || !String(actualQuestion).trim()) {
            alert("Please enter your question");
            return;
        }

        setIsLoadingLocal(true);
        
        // Add conversation to DB
        if (!currentConversationId)
        {
            const { data, error } = await supabase
                .from("conversations")
                .insert([
                    {
                        user_id: user.id,
                        title: actualQuestion.substring(0, 50)
                    }
                ])
                .select()
                .single();

            if (error)
            {
                console.error(error);
                return;
            }

            setConversations(prev => [
                data,
                ...prev
            ]);

            currentConversationId = data.id;

            setConversationId(currentConversationId);
        }

        let insertedUserMessage = null;

        //Save user question to DB
        if (!parentUserMessageId)
        {
            const {data, error} =
                await supabase
                    .from("messages")
                    .insert([
                        {
                            conversation_id: currentConversationId,
                            role: "user",
                            content: actualQuestion
                        }
                    ])
                    .select()
                    .single();

            if (error)
            {
                console.error(
                    "Save User Message Error:",
                    error
                );
                return;
            }

            insertedUserMessage = data;

            parentUserMessageId = data.id;

            setMessages(prev => [...prev, data]);
        }

        const formData = new FormData();

        formData.append("question", actualQuestion);
        formData.append("session_id", session_id);
        formData.append("selected_model", selectedModel);

        if (selectedFile) {
          formData.append("file", selectedFile);
        }

        // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
        //   method: "POST",
        //   body: formData
        // });

        controllerRef.current = new AbortController();

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
            method: "POST",
            body: formData,
            signal: controllerRef.current.signal
        });

        setIsGenerating(true);

        if (!response.body) {
          throw new Error("No response body");
        }

        // EMPTY AI MESSAGE
        let aiMessage = {
          role: "assistant",
          content: "",
          conversation_id: 0,
          id: null,
          image_url: null,
          created_at: null,
          feedback: null,
          parent_user_message_id: parentUserMessageId,
          response_version: responseVersion
        };
        
        //Display latese response
        if (replaceAssistantId)
        {
            setMessages(prev =>
                prev.map(msg =>
                    msg.id === replaceAssistantId
                        ? aiMessage
                        : msg
                )
            );
        }
        else
        {
            setMessages(prev => [...prev, aiMessage]);
        }

        const reader = response.body.getReader();

        const decoder = new TextDecoder();

        let done = false;

        //await delay(500);
        
        //setStatus("Generating final answer...");

        //await delay(500);

        while (!done) {
          const result = await reader.read();

          done = result.done;
          
          const chunk = decoder.decode(result.value || new Uint8Array(), {
            stream: true,
          });

          const lines = chunk.split("\n");

          for (const line of lines) 
          {
            if (!line.startsWith("data:"))
              continue;

            if (line.startsWith("data: "))
            {
                const jsonStr = line.replace("data: ", "").trim();
                
                if (!jsonStr) continue;
                try 
                {
                  const data = JSON.parse(jsonStr);

                  // STATUS
                  if (data.type === "status") {

                    setStatus(data.content);
                  }
                  // STEP
                  else if (data.type === "step")
                  {
                    setSteps((prev) => {

                      const updated = [...prev];

                      const existingIndex = updated.findIndex(x => x.step === data.step);

                      // STEP ALREADY EXISTS
                      if (existingIndex >= 0)
                      {
                        const existingStep = updated[existingIndex];
                        if (data.status === "completed" && existingStep.startedAt)
                        {
                          data.startedAt = existingStep.startedAt;
                          data.duration = Date.now() - existingStep.startedAt;
                        }
                        updated[existingIndex] = {
                            ...existingStep,
                            ...data
                        };
                      }
                      // NEW STEP
                      else
                      {
                        updated.push({
                            ...data,
                            startedAt: Date.now()
                        });
                      }

                      return updated;
                    });

                    //totalDuration = steps.reduce((total, step) => total + (step.duration || 0), 0);

                  }
                   // MESSAGE
                  else if (data.type === "message") {

                    aiMessage.content += data.content;

                    assistantText += data.content;
                    
                    if (replaceAssistantId)
                    {
                      setMessages(prev =>
                          prev.map(msg =>
                              msg.id === replaceAssistantId
                                  ? { ...aiMessage }
                                  : msg
                          )
                      );
                    }
                    else
                    {
                      setMessages((prev) => {

                        const updated = [...prev];

                        updated[updated.length - 1] = {
                          ...aiMessage
                        };

                        return updated;
                      });
                    }                    
                  }
                  else if (data.type === "image")
                  {
                      console.log("IMAGE TYPE");
                      //console.log(data.content);
                      aiMessage.image_url = data.content;

                      console.log(aiMessage);

                      if (replaceAssistantId)
                      {
                          setMessages(prev =>
                              prev.map(msg =>
                                  msg.id === replaceAssistantId
                                      ? { ...aiMessage }
                                      : msg
                              )
                          );
                      }
                      else
                      {
                          setMessages(prev => {

                              const updated = [...prev];

                              updated[updated.length - 1] = {
                                  ...aiMessage
                              };

                              return updated;
                          });

                          console.log(messages);
                      }
                  }

                  // ERROR
                  else if (data.type === "error") {

                    setStatus("");

                    aiMessage.content += "\n❌ " + data.content;
                    
                    if (replaceAssistantId)
                    {
                      setMessages(prev =>
                          prev.map(msg =>
                              msg.id === replaceAssistantId
                                  ? { ...aiMessage }
                                  : msg
                          )
                      );
                    }
                    else
                    {
                      setMessages((prev) => {

                          const updated = [...prev];

                          updated[updated.length - 1] = {
                              ...aiMessage
                          };

                          return updated;
                      });
                    }
                    
                  }
                }
                catch (err) 
                {
                  console.error("JSON Parse Error", err);
                }
                
            }
          }
        }

        //Save AI Response to DB
        const { data } = await supabase
        .from("messages")
        .insert([
            {
                conversation_id: currentConversationId,
                role: "assistant",
                image_url: aiMessage.image_url,
                content: aiMessage.content,
                parent_user_message_id: parentUserMessageId,
                response_version: responseVersion
            }
        ]).select().single();

        //Update version object
        const versions = await loadVersions(parentUserMessageId);
        setResponseBranches(prev => ({
            ...prev,
            [parentUserMessageId]: {
                current: versions.length,
                versions: versions
            }
        }));

        aiMessage.conversation_id = data.conversation_id;
        aiMessage.id = data.id;
        aiMessage.created_at = data.created_at;
        aiMessage.image_url = data.image_url;
        aiMessage.feedback = data.feedback;
        aiMessage.parent_user_message_id = data.parent_user_message_id;
        aiMessage.response_version = data.response_version;
        
        if (replaceAssistantId)
        {
          setMessages(prev =>
              prev.map(msg =>
                  msg.id === replaceAssistantId
                      ? { ...aiMessage }
                      : msg
              )
          );
        }
        else
        {
          setMessages((prev) => {

            const updated = [...prev];

            updated[updated.length - 1] = {
              ...aiMessage
            };

            return updated;
          });
        }

        document.getElementById("txtQuestion").value = "";
        setQuestion("");

        responseSaved = true;

        //speakText(aiMessage.content);
    }
    catch(error)
    {
      if (error.name === "AbortError")
      {
          console.log("Generation stopped");

          if (assistantText.trim() && !responseSaved)
          {
              const { data } = await supabase
                  .from("messages")
                  .insert([
                      {
                          conversation_id: currentConversationId,
                          role: "assistant",
                          content: assistantText,
                          parent_user_message_id: parentUserMessageId,
                          response_version: responseVersion
                      }
                  ]).select().single();
            
            setMessages((prev) => {

              const updated = [...prev];

              updated[updated.length - 1] = {
                ...data
              };

              return updated;
            });

            responseSaved = true;
          }
      }
      else
      {
          console.error(error);
          
          setMessages(prev => {

              const updated = [...prev];

              updated[updated.length - 1] = {
                  role: "assistant",
                  content: "❌ Something went wrong."
              };

              return updated;
          });
      }      
    }
    finally 
    {
      //////setGlobalLoading(false)
      setIsGenerating(false);
      setStatus("");
      setSteps([]);
      setIsLoadingLocal(false);
    }
  };

  const startListening = () => 
  {

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        alert("Speech Recognition not supported in this browser");

        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event) => {

        const transcript = event.results[0][0].transcript;

        setQuestion(transcript);

        askAI(transcript);
    };

    recognition.onerror = (event) => {
        console.log("Speech Error:", event.error);
    };

    recognition.start();
  };
  
  //Speak Response
  const speakText = (messageId, text) => 
  {
    // Stop any existing speech
    window.speechSynthesis.cancel();

    setSpeakingMessageId(messageId);

    const speech = new SpeechSynthesisUtterance(text);

    speech.lang = "en-US";

    speech.onstart = () => {
        setIsSpeaking(true);
        setIsPaused(false);
    };

    speech.onend = () => {
        setIsSpeaking(false);
        setIsPaused(false);
    };

    speech.onerror = () => {
        setIsSpeaking(false);
        setIsPaused(false);
    };

    speakRef.current = speech;

    window.speechSynthesis.speak(speech);
  };

  //Pause Speaking
  const pauseSpeaking = () => {
    window.speechSynthesis.pause();
    setIsPaused(true);
  };

  //Resume Speaking
  const resumeSpeaking = () => {
    window.speechSynthesis.resume();
    setIsPaused(false);
  };

  //Stop Speaking
  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setIsPaused(false);
    setSelectedMessageId(null);
  };

  const startRecording = async () => {

    try {

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true
      });

      const mediaRecorder = new MediaRecorder(stream);

      mediaRecorderRef.current = mediaRecorder;

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {

        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {

        const audioBlob = new Blob(
          audioChunksRef.current,
          {
            type: "audio/webm"
          }
        );

        await uploadAudio(audioBlob);

        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();

      setIsRecording(true);

    } catch (err) {

      console.error(err);

      alert("Microphone permission denied");
    }
  };

  const stopRecording = () => {

    if (mediaRecorderRef.current) {

      mediaRecorderRef.current.stop();

      setIsRecording(false);
    }
  };

  const uploadAudio = async (audioBlob) => {

    try {

      setGlobalLoading(true);

      const formData = new FormData();

      formData.append(
        "audio",
        audioBlob,
        "speech.webm"
      );

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/transcribe`,
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      const transcript = data.transcript;

      setGlobalLoading(false);

      setQuestion(transcript);

      askAI(transcript);

    } catch (err) {
      setGlobalLoading(false);
      console.error(err);

      alert("Failed to transcribe audio");
    }
  };

  // ✅ CALCULATE HERE
    const totalDuration = steps.reduce(

        (total, step) =>
            total + (step.duration || 0),

        0
    );

  //Stop Generating Response
  const stopGenerating = () => {
    if (controllerRef.current) {
        controllerRef.current.abort();
        setIsGenerating(false);
        setIsLoadingLocal(false);
    }
  };
  
  const saveEditedPrompt = async (index) => {

    if (!selectedModel.trim()) {
          alert("Please select AI modal");
          return;
      }
    const editedMessage = messages[index];

    // Update current message
    await supabase
        .from("messages")
        .update({
            content: editingText
        })
        .eq(
            "id",
            editedMessage.id
        );
    
    // Find later messages
    const messagesToDelete = messages.slice(index);
    
    const idsToDelete = messagesToDelete.map(msg => msg.id);

    if (idsToDelete.length > 0)
    {
        await supabase.from("messages").delete().eq("conversation_id",editedMessage.conversation_id).in("id", idsToDelete);
    }

    let updatedMessages = [...messages];

    // Replace user message
    updatedMessages[index].content = editingText;

    // Remove everything after this message
    updatedMessages = updatedMessages.slice(0, index);

    console.log("AFTER");
    console.log(updatedMessages);

    setMessages(updatedMessages);

    setEditingIndex(null);

    // regenerate response
    await askAI(editingText);

  };

  //Regenerate response
  const regenerateResponse = async (assistantMessage) =>
  {
      try
      {
          setGlobalLoading(true);

          const { data: userMessage } =
              await supabase
                  .from("messages")
                  .select("*")
                  .eq(
                      "id",
                      assistantMessage.parent_user_message_id
                  )
                  .single();

          if (!userMessage)
              return;

          //Get latest response version
          const { data: versions } =
              await supabase
                  .from("messages")
                  .select("response_version")
                  .eq(
                      "parent_user_message_id",
                      userMessage.id
                  )
                  .order(
                      "response_version",
                      {
                          ascending:false
                      }
                  )
                  .limit(1);

          const nextVersion =
              versions.length > 0
                  ? versions[0].response_version + 1
                  : 1;

          await askAI(userMessage.content, userMessage.id, nextVersion, assistantMessage.id);
      }
      catch(error)
      {
          console.error(error);
      }
      finally{
        setGlobalLoading(false);
      }
  };

  //Load assistant response(s) by parentUserMessageId
  const loadVersions = async (parentUserMessageId) =>
  {
      const { data, error } =
          await supabase
              .from("messages")
              .select("*")
              .eq(
                  "parent_user_message_id",
                  parentUserMessageId
              )
              .order(
                  "response_version",
                  {
                      ascending: true
                  }
              );

      if (error)
      {
          console.error(error);
          return;
      }

      return data;
  };

  //Copy message
  const copyMessage = async (text) => {
    try {
        await navigator.clipboard.writeText(text);
        toast.success(
            "Copied"
        );
    }
    catch (err) {
        console.error(err);
        toast.error(
            "Copy failed"
        );
    }
};

//Submit Feedback
const submitFeedback = async (messageId, feedback) =>
{
  try
  {
    setGlobalLoading(true);
    const { error } =
        await supabase
            .from("messages")
            .update({
                feedback: feedback
            })
            .eq("id", messageId).select();
    
    if (!error)
    {
        setMessages(prev =>
            prev.map(m =>
                m.id === messageId
                    ? {
                        ...m,
                        feedback
                    }
                    : m
            )
        );
        toast.success(
            "Thanks for your feedback!"
        );
    }
  }
  finally{
    setGlobalLoading(false);
  }
};

const saveFeedback = async () => {
  try
  {
    setGlobalLoading(true);
    await supabase
        .from("messages")
        .update({
            feedback: "dislike",
            feedback_reason: feedbackReason,
            feedback_comment: feedbackComment
        })
        .eq("id", selectedMessageId);

    setMessages(prev =>
        prev.map(m =>
            m.id === selectedMessageId
                ? {
                    ...m,
                    feedback: "dislike",
                    feedback_reason: feedbackReason,
                    feedback_comment: feedbackComment
                }
                : m
        )
    );

    toast.success(
        "Thanks for your feedback!"
    );

    setFeedbackModalOpen(false);
    setFeedbackReason("");
    setFeedbackComment("");
  }
  finally{
    setGlobalLoading(false);
  }
};

//Switch response version
const switchVersion = (assistantMessage, direction) =>
{
  const branch = responseBranches[assistantMessage.parent_user_message_id];

  if (!branch)
  {
      return;
  }

  const current = branch.current;

  const newVersion = current + direction;

  //Validation
  if (newVersion < 1 || newVersion > branch.versions.length)
  {
      return;
  }

  const selectedVersion = branch.versions[newVersion - 1];

  //Display selected version
  setMessages(prev =>
    prev.map(msg =>
    {
        if (msg.id === assistantMessage.id)
        {
            return selectedVersion;
        }

        return msg;
    })
  );

  setResponseBranches(prev => ({
    ...prev,
    [assistantMessage.parent_user_message_id]:
    {
        ...branch,

        current: newVersion
    }
  }));
}

  return (
    <>
      {/* <div className="font-[Inter] max-w-5xl mx-auto bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden flex flex-col h-[90vh]"> */}
      <div className="font-[Inter] h-full bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden flex flex-col">

        <div className="border-b px-6 py-4 bg-white flex justify-between items-center">

          <div>

              <h2 className="text-xl font-bold">
                  General AI Assistant
              </h2>

              <div className="text-sm text-gray-500">
                  Ask anything
              </div>

          </div>

        </div>

        {messages && (

          <div className="flex-1 overflow-y-auto px-6 py-6 bg-[#f9f7f3]">
              
              {messages.map((msg, index) => (                
                  
                  <motion.div key={index} initial={{ opacity: 0, y: 10}} animate={{ opacity: 1, y: 0 }} transition={{duration: 0.2}}>
                    <div key={index} className={msg.role === "user"? "text-right": "text-left"}>
                      <div
                          className={
                          msg.role === "user"
                              ? "group inline-block mt-3 mb-1 px-5 py-1  max-w-[80%] text-[15px] leading-7"
                              : "group bg-white/90 backdrop-blur-md border border-gray-100 border-gray-200 text-black inline-block px-5 py-4 rounded-3xl w-full shadow-sm text-[15px] leading-7"
                          }
                      >
                        {
                          editingIndex === index ?
                          (
                            <div>
                                <textarea
                                    value={editingText}
                                    onChange={(e)=>setEditingText(e.target.value)}
                                    className="w-full border rounded-xl p-1"
                                />

                                <div className="mt-2 flex gap-2">

                                    <button
                                        onClick={() => saveEditedPrompt(index)}
                                        className="bg-blue-500 text-white px-4 py-2 rounded-xl"
                                    >
                                        Save
                                    </button>

                                    <button
                                        onClick={() => setEditingIndex(null)}
                                        className="bg-gray-300 px-4 py-2 rounded-xl"
                                    >
                                        Cancel
                                    </button>

                                </div>
                            </div>
                          )
                          :
                          (                            
                            <div className="text-white prose prose-lg max-w-none">

                              <>
                              {msg.image_url && (
                                  <img
                                      src={msg.image_url}
                                      alt="Generated"
                                      className="mt-3 rounded-xl border shadow max-w-full"
                                      loading="lazy"
                                  />

                              )}
                              {msg.content && (
                              <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}
                                            components={{
                                                h1: ({ children }) => (
                                                    <h1 className="text-3xl font-bold mt-8 mb-4 text-gray-900">
                                                        {children}
                                                    </h1>
                                                ),
                                                h2: ({ children }) => (
                                                    <h2 className="text-2xl font-semibold mt-7 mb-3 text-gray-800">
                                                        {children}
                                                    </h2>
                                                ),
                                                h3: ({ children }) => (
                                                    <h3 className="text-xl font-semibold mt-6 mb-2 text-gray-800">
                                                        {children}
                                                    </h3>
                                                ),
                                                p: ({ children }) => (
                                                    <div className={
                                                          msg.role === "user"
                                                              ? "leading-8 text-[15px] text-gray-800 mb-1 break-words rounded-3xl shadow-sm px-3 py-1"
                                                              : "leading-8 text-[15px] text-gray-800 mb-1 break-words"
                                                          }>
                                                      {children}
                                                    </div>
                                                ),
                                                ul: ({ children }) => (
                                                    <ul className="list-disc ml-6 mb-4 space-y-2">
                                                        {children}
                                                    </ul>
                                                ),
                                                ol: ({ children }) => (
                                                    <ol className="list-decimal ml-6 mb-4 space-y-2">
                                                        {children}
                                                    </ol>
                                                ),
                                                li: ({ children }) => (
                                                    <li className="leading-7 text-gray-800">
                                                        {children}
                                                    </li>
                                                ),
                                                blockquote: ({ children }) => (
                                                    <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 my-4">
                                                        {children}
                                                    </blockquote>
                                                ),
                                                img: ({ src, alt }) => (
                                                  <div className="my-6">
                                                      <img src={src} alt={alt} className="rounded-2xl border border-gray-200 shadow-lg hover:shadow-xl hover:scale-[1.01] transition-all duration-300 max-w-full" />
                                                      {alt && (
                                                          <div className="text-center text-sm text-gray-500 mt-2">
                                                              {alt}
                                                          </div>
                                                      )}
                                                  </div>
                                              ),
                                                code({ inline, className, children }) {

                                                    const text = String(children).replace(/\n$/, "");

                                                    /*
                                                    -----------------------------
                                                    CHART BLOCK
                                                    -----------------------------
                                                    */
                                                    if (className === "language-chart")
                                                    {
                                                      try 
                                                      {
                                                          const chartData = JSON.parse(text);

                                                          return (
                                                              <CustomChart data={chartData} />
                                                          );

                                                      }
                                                      catch
                                                      {
                                                          return (
                                                              <div className="text-red-500 text-sm">
                                                                  Invalid chart data
                                                              </div>
                                                          );
                                                      }
                                                    }

                                                    /*
                                                      -----------------------------
                                                      CODE SYNTAX HIGHLIGHTING
                                                      -----------------------------
                                                      */

                                                    const match = /language-(\w+)/.exec(className || "");
                                                    if(!inline && match)
                                                    {
                                                      return (
                                                        <div className="relative rounded-xl overflow-hidden">
                                                          <div className="bg-slate-800 px-4 py-2 flex justify-between text-sm text-white">
                                                              <span>{match[1].toUpperCase()}</span>
                                                              <button className="cursor-pointer" 
                                                                      onClick={() => {
                                                                        navigator.clipboard.writeText(text);
                                                                        toast.success("Copied!");
                                                                      }}
                                                              >
                                                                  📋 Copy
                                                              </button>
                                                          </div>
                                                          
                                                            <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div"
                                                                customStyle={{
                                                                    borderRadius: "16px",
                                                                    padding: "20px",
                                                                    fontSize: "14px",
                                                                    marginTop: "20px",
                                                                    marginBottom: "20px"
                                                                }}
                                                            >
                                                                {text}
                                                            </SyntaxHighlighter>
                                                        </div>
                                                      );
                                                    }

                                                    /*
                                                    -----------------------------
                                                    INLINE CODE
                                                    -----------------------------
                                                    */
                                                    if (inline) {

                                                        return (
                                                          <code className="bg-gray-100 text-pink-600 px-1.5 py-0.5 rounded text-sm">
                                                            {children}
                                                          </code>
                                                        );
                                                    }

                                                    return (
                                                      <code className={className}>
                                                        {children}
                                                      </code>
                                                    );

                                                },

                                                // pre: ({ children }) => (
                                                //     <pre className="bg-[#0d1117] text-gray-100 p-5 rounded-2xl overflow-x-auto text-sm leading-7 my-5 shadow-lg">
                                                //         {children}
                                                //     </pre>
                                                // ),
                                                pre: ({ children }) => (
                                                  <pre className="whitespace-pre-wrap break-words overflow-x-auto bg-slate-900 p-4 rounded-xl">
                                                    {children}
                                                  </pre>
                                                ),
                                                table: ({ children }) => (
                                                    <div className="overflow-x-auto my-6">
                                                        <table className="min-w-full border border-gray-200 rounded-2xl overflow-hidden text-sm">
                                                            {children}
                                                        </table>
                                                    </div>
                                                ),
                                                thead: ({ children }) => (
                                                    <thead className="bg-gray-100">
                                                        {children}
                                                    </thead>
                                                ),
                                                th: ({ children }) => (
                                                    <th className="bg-gray-100 px-4 py-3 border-b text-left font-semibold">
                                                        {children}
                                                    </th>
                                                ),
                                                td: ({ children }) => (
                                                    <td className="px-4 py-3 border-b text-gray-700">
                                                        {children}
                                                    </td>
                                                )
                                            }}
                                        >
                                            {msg.content}
                              </ReactMarkdown>
                              )}

                              </>

                                {msg.role === "user" && (
                                  <div className="flex justify-end mt-0">
                                      <button
                                        title="Copy"
                                        className="cursor-pointer opacity-0 group-hover:opacity-100 group-hover:opacity-100 text-gray-400 hover:text-gray-700 text-sm"
                                        onClick={() => {copyMessage(msg.content);}}
                                    >📋</button>

                                      <button title="Edit Prompt"
                                          onClick={() => {
                                              setEditingIndex(index);
                                              setEditingText(msg.content);
                                          }}
                                          className="cursor-pointer opacity-0 group-hover:opacity-100 group-hover:opacity-100 text-gray-400 hover:text-gray-700 ml-2"
                                      >
                                          ✏
                                      </button>
                                    </div>
                                )}
                              
                              {msg.role === "assistant" && (

                                <div className="flex items-center gap-2 mt-2">
                                    <button title="Copy"
                                        className="cursor-pointer text-gray-400 hover:text-gray-700 text-sm"
                                        onClick={() => {copyMessage(msg.content);}}
                                    >📋</button>

                                    {/* <button title="Regenerate"
                                        className="cursor-pointer text-gray-400 hover:text-gray-700 ml-2"
                                        onClick={() => regenerateResponse(msg)}
                                    >🔄</button> */}

                                    <button className="cursor-pointer" title="Like"
                                        onClick={() => submitFeedback(msg.id, "like")}
                                    >
                                      {
                                          msg.feedback === "like"
                                          ?
                                          <HandThumbUpSolid className="w-5 h-5 text-green-600"/>
                                          :
                                          <HandThumbUpIcon className="w-5 h-5 text-gray-400"/>
                                      }
                                    </button>

                                    <button className="cursor-pointer" title="Dislike"
                                        onClick={() => {
                                            setSelectedMessageId(msg.id);
                                            setFeedbackModalOpen(true);
                                        }}
                                    >
                                      {
                                          msg.feedback === "dislike"
                                          ?
                                          <HandThumbDownSolid className="w-5 h-5 text-red-600"/>
                                          :
                                          <HandThumbDownIcon className="w-5 h-5 text-gray-400"/>
                                      }
                                    </button>
                                    
                                    {(!isSpeaking || (isSpeaking && speakingMessageId != msg.id) || speakingMessageId == null) && (
                                    <button onClick={() => speakText(msg.id, msg.content)} title="Play" 
                                    className="cursor-pointer text-gray-500 hover:text-black">▶</button>
                                    )}
                                    
                                    {speakingMessageId == msg.id && isSpeaking && (
                                      <>
                                        <button title={isPaused ? "Resume" : "Pause"} className="cursor-pointer text-gray-500 hover:text-black"
                                         onClick={
                                                isPaused
                                                    ? resumeSpeaking
                                                    : pauseSpeaking
                                            }
                                        >
                                            {isPaused ? "▶" : "⏸"}
                                        </button>

                                        <button className="cursor-pointer text-gray-500 hover:text-black"
                                            onClick={stopSpeaking}
                                        >
                                            ⏹
                                        </button>
                                      </>
                                      )}
                                      

                                </div>
                                )
                              }

                              {/* {
                                msg.role === "assistant" &&
                                msg.parent_user_message_id &&
                                responseBranches[msg.parent_user_message_id] &&
                                (
                                    <div className="flex items-center gap-2 mt-3">
                                        <button disabled={responseBranches[msg.parent_user_message_id].current <= 1} onClick={() =>switchVersion(msg, -1)}>
                                            ◀
                                        </button>
                                        <span>
                                            {
                                                responseBranches[msg.parent_user_message_id].current
                                            }
                                            /
                                            {
                                                responseBranches[msg.parent_user_message_id].versions.length
                                            }
                                        </span>
                                        <button disabled={responseBranches[msg.parent_user_message_id].current >= responseBranches[msg.parent_user_message_id].versions.length} onClick={() =>switchVersion(msg, 1)}>
                                            ▶
                                        </button>
                                    </div>
                                )
                            } */}
                            </div>
                          )
                        }
                      </div>
                    </div>
                  </motion.div>
              ))}
              </div>
        )}

        <div ref={messagesEndRef}></div>

        {status && (
          <div className="text-sm text-gray-500 mb-2 animate-pulse">
            {status}
          </div>
        )}

        
        {steps && steps.length > 0 && (        
          <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-4 mb-3">
            <div className="flex items-center gap-2 font-semibold mb-2">
              <div className="w-3 h-3 border border-gray-300 border-t-blue-500 rounded-full animate-spin" />
              Agent Steps ({steps.length})
              <div className="text-gray-500 text-sm">
                  • {(totalDuration / 1000).toFixed(1)}s
              </div>
            </div>
            {steps.map((step, indexS) => (                      
                <div key={indexS} className="flex items-center gap-2 text-sm mb-1 ">

                  {step.status === "running"}

                  {step.status === "completed"}

                  {step.status === "error" && "❌"}

                  <span><span className="text-gray-500 text-xs">{(indexS + 1).toString().padStart(2, "0")}.</span> {step.icon} {step.step}</span>

                  <span className="text-gray-500 text-xs">
                    {step.duration ? `(${(step.duration / 1000).toFixed(1)}s)` : ""}
                  </span>
                </div>            
            ))}
          </div>
        )}
        
        <div className="border-t bg-white p-4">

    {/* FILE PREVIEW */}
    {selectedFile && (
      <div className="mb-3">

        {selectedFile.type.startsWith("image/") ? (
          <div className="relative inline-block">

            <img
              src={URL.createObjectURL(selectedFile)}
              alt="Preview"
              className="w-24 h-24 object-cover rounded-xl border"
            />

            <button
              onClick={() => setSelectedFile(null)}
              className="absolute -top-2 -right-2 bg-white rounded-full shadow p-1 text-red-500 hover:text-red-700"
            >
              ✕
            </button>

          </div>
        ) : (isAudioFile(selectedFile) ? (
            <div className="bg-gray-100 rounded-xl p-3">
              <div className="font-medium mb-2">
                🎵 {selectedFile.name}
              </div>

              <audio
                controls
                className="w-full"
                src={URL.createObjectURL(selectedFile)}
              />
              <button onClick={() => setSelectedFile(null)} className="text-red-500 hover:text-red-700">✕</button>
            </div>
            
            ) : (

          <div className="flex items-center justify-between bg-gray-100 rounded-xl px-4 py-3">

            <div className="flex items-center gap-3">
              <span className="text-2xl">📄</span>

              <div>
                <div className="font-medium text-sm">
                  {selectedFile.name}
                </div>

                {/* <div className="text-xs text-gray-500">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </div> */}
              </div>
            </div>

            <button
              onClick={() => setSelectedFile(null)}
              className="text-red-500 hover:text-red-700"
            >
              ✕
            </button>

          </div>
        ))}
      </div>
    )}

    {/* CHAT INPUT AREA */}
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      className={`
        relative
        border
        rounded-3xl
        p-3
        transition-all
        duration-200
        ${
          isDragging
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300"
        }
      `}
    >

      {/* DRAG OVERLAY */}
      {isDragging && (
        <div className="absolute inset-0 z-20 bg-blue-50 border-2 border-dashed border-blue-500 rounded-3xl flex flex-col items-center justify-center">

          <div className="text-5xl mb-2">
            📂
          </div>

          <div className="font-semibold">
            Drop file here
          </div>

          <div className="text-sm text-gray-500">
            PDF, Word, Excel, Images, Text
          </div>

        </div>
      )}

      <div className="flex items-end gap-3">

        {/* MODEL */}
        <select
          className="border rounded-2xl px-3 py-2 bg-white"
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
        >
          <option value="">Model</option>
          <option value="gemini">Gemini</option>
          <option value="openai">OpenAI</option>
          <option value="claude">Claude</option>
          <option value="grok">Grok</option>
          <option value="openrouter">OpenRouter</option>
          <option value="groq">Groq</option>
        </select>

        {/* TEXTAREA */}
        <div className="flex-1 relative">

          <input type="text" id="txtQuestion" name="txtQuestion"
            ref={inputRef}
            value={question}
            onKeyDown={handleSearchKeyDown}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Message AI Assistant..."
            className="w-full resize-none outline-none px-10 py-2"
          />

          {/* ATTACH BUTTON */}
          <button
            type="button"
            onClick={() => fileInputRef.current.click()}
            className="absolute left-2 bottom-3 text-gray-500 hover:text-black"
          >
            <PaperClipIcon className="w-5 h-5 cursor-pointer" />
          </button>

          <input
            type="file"
            ref={fileInputRef}
            hidden
            onChange={(e) => {
              if (e.target.files?.length) {
                setSelectedFile(e.target.files[0]);
              }
            }}
          />

        </div>

        {speechSupported ? (
          <button onClick={startListening} className="bg-black text-white rounded-full w-12 h-12 flex items-center justify-center hover:opacity-90"
            title="Speak">🎤</button>
          ) : (
          <button onClick={isRecording ? stopRecording : startRecording }
                className={`rounded-full w-12 h-12 flex items-center justify-center ${
                            isRecording
                              ? "bg-red-500 text-white"
                              : "bg-gray-200"
                          }`}
          >{isRecording ? "⏹" : "🎤"}</button>
          )}
        
          {
            isLoadingLocal ?
            (
              isGenerating ?

              <button title="Stop" onClick={stopGenerating} className="bg-black text-white rounded-full w-12 h-12 flex items-center justify-center hover:opacity-90">
                  ■
              </button>
              :
              <button disabled className="bg-black text-white rounded-full w-12 h-12 flex items-center justify-center hover:opacity-90">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              </button>
            )
            :
            <button title="Send" onClick={() => askAI()} className="bg-black text-white rounded-full w-12 h-12 flex items-center justify-center hover:opacity-90">
                ➤
            </button>
          }

        </div>
      </div>
    </div>
  </div>

  {
    feedbackModalOpen && (

    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">

        <div className="bg-white rounded-2xl p-6 w-[450px]">

            <h2 className="text-xl font-semibold mb-4 text-gray-800">
                Why didn't you like this response?
            </h2>

            <div className="space-y-3 text-gray-700">

                <label className="flex gap-2">
                    <input
                        type="radio"
                        value="Incorrect"
                        checked={feedbackReason==="Incorrect"}
                        onChange={(e)=>setFeedbackReason(e.target.value)}
                    />
                    Incorrect
                </label>

                <label className="flex gap-2">
                    <input
                        type="radio"
                        value="Hallucinated"
                        checked={feedbackReason==="Hallucinated"}
                        onChange={(e)=>setFeedbackReason(e.target.value)}
                    />
                    Hallucinated
                </label>

                <label className="flex gap-2">
                    <input
                        type="radio"
                        value="Didn't answer question"
                        checked={feedbackReason==="Didn't answer question"}
                        onChange={(e)=>setFeedbackReason(e.target.value)}
                    />
                    Didn't answer question
                </label>

                <label className="flex gap-2">
                    <input
                        type="radio"
                        value="Too short"
                        checked={feedbackReason==="Too short"}
                        onChange={(e)=>setFeedbackReason(e.target.value)}
                    />
                    Too short
                </label>

                <label className="flex gap-2">
                    <input
                        type="radio"
                        value="Offensive"
                        checked={feedbackReason==="Offensive"}
                        onChange={(e)=>setFeedbackReason(e.target.value)}
                    />
                    Offensive
                </label>

            </div>

            <textarea
                value={feedbackComment}
                onChange={(e)=>setFeedbackComment(e.target.value)}
                placeholder="Additional comments..."
                className="w-full border rounded-xl p-3 mt-5"
                rows={4}
            />

            <div className="flex justify-end gap-3 mt-5">

                <button
                    className="px-4 py-2 rounded-xl bg-gray-300"
                    onClick={()=>{
                        setFeedbackModalOpen(false);
                    }}
                >
                    Cancel
                </button>

                <button
                    className="px-4 py-2 rounded-xl bg-red-500 text-white"
                    onClick={saveFeedback}
                >
                    Submit
                </button>

            </div>

        </div>

    </div>

    )
    }
    </>
  );
}