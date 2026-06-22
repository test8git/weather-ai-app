"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"

export default function LoginPage() {
  const { setGlobalLoading } = useLoading();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const login = async () => 
    {
      try 
      {
        setGlobalLoading(true);
        const { data, error } =
            await supabase.auth.signInWithPassword({
                email,
                password
            });

        // console.log("LOGIN DATA:", data);
        // console.log("LOGIN ERROR:", error);

        if (error) {
            alert(error.message);
            return;
        }

        const sessionResult =
            await supabase.auth.getSession();

        // console.log("SESSION AFTER LOGIN:", sessionResult.data.session);

        router.push("/");
      }
      finally {
        setGlobalLoading(false);
      }
    };

  return (

    <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500">

      <div className="bg-white p-8 rounded-3xl shadow-xl w-full max-w-md">

        <h1 className="text-3xl font-bold text-center mb-6">
          General AI Assistant
        </h1>

        <input
          type="email"
          placeholder="Email"
          className="w-full border p-3 rounded-xl mb-3"
          value={email}
          onChange={(e)=>setEmail(e.target.value)}
        />

        <input
          type="password"
          placeholder="Password"
          className="w-full border p-3 rounded-xl mb-4"
          value={password}
          onChange={(e)=>setPassword(e.target.value)}
        />

        <div className="flex justify-end mb-4">

            <button
                type="button"
                onClick={() => router.push("/forgot-password")}
                className="text-sm text-blue-600 hover:underline"
            >
                Forgot Password?
            </button>

        </div>

        <button
          onClick={login}
          className="w-full bg-black text-white p-3 rounded-xl"
        >
          Login
        </button>

        <div className="text-center mt-4">

            <span className="text-gray-500">
                Don't have an account?
            </span>

            <button
                onClick={() => router.push("/signup")}
                className="ml-2 text-indigo-600 font-semibold hover:underline"
            >
                Sign Up
            </button>
        </div>

      </div>

    </div>
  );
}