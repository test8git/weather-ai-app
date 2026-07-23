"use client";
import AuthLayout from "@/components/AuthLayout";
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

    <AuthLayout icon="🤖" title="Welcome Back" subtitle="Login to your AI workspace">

        {/* Email */}

        <div className="relative">

            <EnvelopeIcon className="w-5 h-5 absolute left-4 top-4 text-gray-400"/>

            <input
                type="email"
                value={email}
                onChange={(e)=>setEmail(e.target.value)}
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

        {/* Password */}

        <div className="relative mt-5">

            <LockClosedIcon className="w-5 h-5 absolute left-4 top-4 text-gray-400"/>

            <input
                type="password"
                value={password}
                onChange={(e)=>setPassword(e.target.value)}
                placeholder="Password"
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

        <div className="flex justify-end mt-4">

            <button
                onClick={()=>router.push("/forgot-password")}
                className="cursor-pointer text-sm text-indigo-600 hover:underline"
            >
                Forgot Password?
            </button>

        </div>

        <button
            onClick={login}
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
            Login
        </button>

        <div className="text-center mt-8">

            <span className="text-gray-500">
                Don't have an account?
            </span>

            <button
                onClick={()=>router.push("/signup")}
                className="cursor-pointer ml-2 font-semibold text-black"
            >
                Sign Up
            </button>

        </div>

    </AuthLayout>   

  );
}