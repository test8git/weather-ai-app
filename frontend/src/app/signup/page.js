"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"
import { EnvelopeIcon, LockClosedIcon } from "@heroicons/react/24/outline";

export default function SignupPage() {

  const { setGlobalLoading } = useLoading();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const router = useRouter();

  const signup = async () => {

    // Email

    if(email.trim() === ""){

        toast.error("Please enter your email address.");

        return;

    }

    // Password

    if(password === ""){

        toast.error("Please enter your password.");

        return;

    }

    // Confirm Password

    if(confirmPassword === ""){

        toast.error("Please confirm your password.");

        return;

    }

    // Match

    if(password !== confirmPassword){

        toast.error("Passwords do not match.");

        return;

    }

    // Length

    if(password.length < 8){

        toast.error("Password must be at least 8 characters.");

        return;

    }

    try{

        setGlobalLoading(true);

        const { error } = await supabase.auth.signUp({

            email,

            password

        });

        if(error){

            toast.error(error.message);

            return;

        }

        toast.success(
            "Account created successfully! Please check your email to verify your account."
        );

        router.push("/login");

    }
    finally{

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
                🤖
            </div>

            <h1 className="text-4xl font-bold text-white">
                Create Account
            </h1>

            <p className="text-white/80 mt-2 leading-7">
                Create your AI Assistant account and start chatting.
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

        {/* Password */}

        <div className="mt-4 relative">

            <span className="absolute left-4 top-4 text-white">
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
                    pr-12
                    py-4
                    outline-none
                    focus:border-blue-300
                "
            />

        </div>

        {/* Confirm Password */}

        <div className="mt-4 relative">

            <span className="absolute left-4 top-4 text-white">
                <LockClosedIcon className="w-5 h-5" />
            </span>

            <input
                type="password"
                placeholder="Confirm Password"
                value={confirmPassword}
                onChange={(e)=>setConfirmPassword(e.target.value)}
                className="
                    w-full
                    rounded-xl
                    bg-white/10
                    border
                    border-white/20
                    text-white
                    placeholder-white/60
                    pl-12
                    pr-12
                    py-4
                    outline-none
                    focus:border-blue-300
                "
            />

        </div>

        {/* Password Hint */}

        {/* <p className="mt-3 text-sm text-white/70 leading-6">

            Password should contain at least
            <span className="font-semibold text-white">
                {" "}8 characters
            </span>
            ,
            one uppercase letter,
            one lowercase letter,
            one number,
            and one special character.

        </p> */}

        {/* Signup */}

        <button
            onClick={signup}
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
            Create Account →
        </button>

        {/* Divider */}

        <div className="flex items-center my-8">

            <div className="flex-1 h-px bg-white/20" />

            <div className="flex-1 h-px bg-white/20" />

        </div>

        {/* Login */}

        <div className="text-center">

            <span className="text-white/70">
                Already have an account?
            </span>

            <button
                onClick={() => router.push("/login")}
                className="
                    cursor-pointer
                    ml-2
                    text-white
                    font-semibold
                    hover:text-blue-200
                    transition
                "
            >
                Login
            </button>

        </div>

    </div>

</div>
  );
}