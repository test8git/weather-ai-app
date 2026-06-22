"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"

export default function SignupPage() {

  const { setGlobalLoading } = useLoading();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const signup = async () => {
    try 
    {
        setGlobalLoading(true);
        const { error } =
        await supabase.auth.signUp({
            email,
            password
        });

        if (error) {

        alert(error.message);

        return;
        }

        alert("Account created");
    }
    finally {
        setGlobalLoading(false);
    }
  };

  return (

    <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-blue-500 to-indigo-600">

      <div className="bg-white p-8 rounded-3xl shadow-xl w-full max-w-md">

        <h1 className="text-3xl font-bold text-center mb-6">
          Create Account
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

        <button
          onClick={signup}
          className="w-full bg-indigo-600 text-white p-3 rounded-xl"
        >
          Sign Up
        </button>
        <div className="text-center mt-4">

            <span className="text-gray-500">
                Already have an account?
            </span>

            <button
                onClick={() => router.push("/login")}
                className="ml-2 text-indigo-600 font-semibold hover:underline"
            >
                Login
            </button>
        </div>
      </div>

    </div>
  );
}