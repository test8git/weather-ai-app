"use client";

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

    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-700 via-purple-600 to-pink-500">

    {/* Background */}

    <div className="absolute w-96 h-96 bg-pink-400 rounded-full blur-[120px] opacity-25 top-[-100px] left-[-100px]" />

    <div className="absolute w-96 h-96 bg-indigo-400 rounded-full blur-[120px] opacity-25 bottom-[-100px] right-[-100px]" />

    {/* Card */}

    <div
        className="
            relative
            w-full
            max-w-md
            rounded-3xl
            border
            border-white/20
            bg-white/15
            backdrop-blur-xl
            shadow-2xl
            p-10
        "
    >

        {/* Logo */}

        <div className="text-center">

            <div className="text-6xl mb-2">
                🔑
            </div>

            <h1 className="text-4xl font-bold text-white">
                Forgot Password
            </h1>

            <p className="text-white/80 mt-2 leading-7">
                Enter your registered email address and we'll send you a password reset link.
            </p>

        </div>

        {/* Email */}

        <div className="mt-8 relative">

            <span className="absolute left-4 top-4 text-white">
                <EnvelopeIcon className="w-5 h-5" />
            </span>

            <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e)=>setEmail(e.target.value)}
                className="
                    w-full
                    rounded-xl
                    bg-white/10
                    border
                    border-white/20
                    text-white
                    placeholder-white/60
                    pl-12
                    pr-4
                    py-4
                    outline-none
                    focus:border-blue-300
                "
            />

        </div>

        {/* Button */}

        <button
            onClick={sendResetEmail}
            className="
                cursor-pointer
                mt-6
                w-full
                rounded-xl
                py-4
                text-lg
                font-semibold
                text-white
                bg-gradient-to-r
                from-blue-500
                via-purple-500
                to-pink-500
                hover:scale-[1.02]
                transition
                duration-200
                shadow-xl
            "
        >
            Send Reset Link →
        </button>

        {/* Divider */}

        <div className="flex items-center my-8">

            <div className="flex-1 h-px bg-white/20" />

            <div className="flex-1 h-px bg-white/20" />

        </div>

        {/* Back */}

        <div className="text-center">

            <Link
                href="/login"
                className="
                    text-white
                    hover:text-blue-200
                    transition
                    font-medium
                "
            >
                ← Back to Login
            </Link>

        </div>

    </div>

</div>
  );
}