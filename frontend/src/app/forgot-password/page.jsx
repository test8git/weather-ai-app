"use client";

import AuthLayout from "@/components/AuthLayout";
import { useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { EnvelopeIcon } from "@heroicons/react/24/outline";
import { useLoading } from "@/context/LoadingContext"
import Link from "next/link";

export default function ForgotPasswordPage() {

  const [email, setEmail] = useState("");
  const { setGlobalLoading } = useLoading();
  const router = useRouter();

  const sendResetEmail = async () => {
    if (!email) 
    {
        toast.error("Please enter email");
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

          toast.error(error.message);

          return;
      }

      toast.success(
        "Password reset email sent."
      );
    }
    finally {
      setGlobalLoading(false);
    }
  };

  return (

    <AuthLayout icon="🔑" title="Forgot Password" 
                subtitle="Enter your registered email address and we'll send you a password reset link.">

        {/* Email */}

        <div className="relative">

            <EnvelopeIcon
                className="w-5 h-5 absolute left-4 top-4 text-gray-400"
            />

            <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Email Address"
                className="
                    w-full
                    h-14
                    border
                    rounded-xl
                    pl-12
                    pr-4
                    text-base
                    outline-none
                    focus:border-indigo-500
                "
            />

        </div>

        {/* Button */}

        <button
            onClick={sendResetEmail}
            className="
                cursor-pointer
                w-full
                mt-6
                bg-[#0B1324]
                text-white
                rounded-lg
                py-3
                font-semibold
                hover:bg-black
                transition
            "
        >
            Send Reset Link
        </button>

        {/* Back */}

        <div className="text-center mt-8">

            <button
                onClick={() => router.push("/login")}
                className="
                    cursor-pointer
                    text-indigo-600
                    hover:underline
                    font-medium
                "
            >
                ← Back to Login
            </button>

        </div>
    </AuthLayout>            
  );
}