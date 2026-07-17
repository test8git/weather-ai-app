"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"
import { EnvelopeIcon, LockClosedIcon } from "@heroicons/react/24/outline";

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

        if (error) {
            toast.error(error.message);
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

    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-700 via-purple-600 to-pink-500">

    {/* Background Decorations */}

    <div className="absolute w-96 h-96 bg-pink-400 rounded-full blur-[120px] opacity-25 top-[-100px] left-[-100px]" />

    <div className="absolute w-96 h-96 bg-indigo-400 rounded-full blur-[120px] opacity-25 bottom-[-100px] right-[-100px]" />

    {/* Login Card */}

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
                🤖
            </div>

            <h1 className="text-4xl font-bold text-white">
                General AI Assistant
            </h1>

            <p className="text-white/80 mt-2">
                Your intelligent AI workspace
            </p>

        </div>

        {/* Email */}

        <div className="mt-8 relative">

            <span className="absolute left-4 top-4 text-xl">
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

        {/* Password */}

        <div className="mt-4 relative">

            <span className="absolute left-4 top-4 text-xl">
                <LockClosedIcon className="w-5 h-5" />
            </span>

            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e)=>setPassword(e.target.value)}
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

        {/* Remember + Forgot */}

        <div className="flex justify-between items-center mt-4 text-sm">

            <div></div>

            {/* <label className="flex items-center gap-2 text-white">

                <input type="checkbox" />

                Remember me

            </label> */}

            <button
                type="button"
                onClick={() => router.push("/forgot-password")}
                className="cursor-pointer text-blue-200 hover:text-white transition"
            >
                Forgot Password?
            </button>

        </div>

        {/* Login */}

        <button
            onClick={login}
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
            Login →
        </button>

        {/* Divider */}

        <div className="flex items-center my-8">

            <div className="flex-1 h-px bg-white/20" />

            {/* <span className="mx-4 text-white/70">
                OR
            </span> */}

            <div className="flex-1 h-px bg-white/20" />

        </div>

        {/* Social */}

        {/* <div className="grid grid-cols-3 gap-3">

            <button className="bg-white rounded-xl py-3 hover:scale-105 transition">
                Google
            </button>

            <button className="bg-white rounded-xl py-3 hover:scale-105 transition">
                GitHub
            </button>

            <button className="bg-white rounded-xl py-3 hover:scale-105 transition">
                Microsoft
            </button>

        </div> */}

        {/* Signup */}

        <div className="text-center mt-8">

            <span className="text-white/70">
                Don't have an account?
            </span>

            <button
                onClick={() => router.push("/signup")}
                className="cursor-pointer ml-2 text-white font-semibold hover:text-blue-200 transition"
            >
                Sign Up
            </button>

        </div>

    </div>

</div>
  );
}