"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"
import Link from "next/link";

export default function ForgotPasswordPage() {

  const [email, setEmail] = useState("");
  const { setGlobalLoading } = useLoading();
  const router = useRouter();

  const sendResetEmail = async () => {
    if (!email) 
    {
        alert("Please enter email");
        return;
    }
    try 
      {
        setGlobalLoading(true);
        const { error } =
          await supabase.auth.resetPasswordForEmail(
            email,
            {
              redirectTo: `${process.env.NEXT_PUBLIC_APP_URL}/reset-password`
            }
          );

        if (error) {

          alert(error.message);

          return;
      }

      alert(
        "Password reset email sent."
      );
    }
    finally {
      setGlobalLoading(false);
    }
  };

  return (

    <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-blue-500 to-purple-500">

      <div className="bg-white p-8 rounded-3xl shadow-xl w-full max-w-md">

        <h1 className="text-3xl font-bold mb-6 text-center">
          Forgot Password
        </h1>

        <input
          type="email"
          placeholder="Email Address"
          className="w-full border p-3 rounded-xl mb-4"
          value={email}
          onChange={(e)=>setEmail(e.target.value)}
        />
        
        <button
          onClick={sendResetEmail}
          className="w-full bg-indigo-600 text-white p-3 rounded-xl"
        >
          Send Reset Link
        </button>
        <div className="text-center mt-4">
          <Link href="/login" className="text-indigo-600 hover:underline">
            ← Back to Login
          </Link>
        </div>
      </div>

    </div>
  );
}