"use client";
import AuthLayout from "@/components/AuthLayout";
import { useState, useRef } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"
import { EnvelopeIcon, LockClosedIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";

export default function LoginPage() {
  const { setGlobalLoading } = useLoading();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const router = useRouter();
  
  const emailRef = useRef(null);
  const passwordRef = useRef(null);

  const login = async () => 
{
    try 
    {
    if (!email.trim()){toast.error("Please enter email"); return;}
    if (!password.trim()){toast.error("Please enter password"); return;}

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

//Sign in using Google or Github
const singInOAuth = async(provider) =>
{
    try
    {
        setGlobalLoading(true);
        const { error } = await supabase.auth.signInWithOAuth({
            provider: provider,
            options: {
                redirectTo:
                    `${process.env.NEXT_PUBLIC_APP_URL}/auth/callback`

            }
        });
        if (error)
            toast.error(error);
    }
    finally 
    {
        setGlobalLoading(false);
    }
};


  return (

    <AuthLayout
    icon="🤖"
    title="Login"
    subtitle=""
>

    {step === 1 ? (

        <>
            {/* Email */}

            <div className="relative">

                <EnvelopeIcon
                    className="absolute left-4 top-4 w-5 h-5 text-gray-400"
                />

                <input ref={emailRef} type="email" value={email} onChange={(e) => setEmail(e.target.value)} 
                    onKeyDown={(e) => {
                        if (e.key === "Enter") {
                            if (!email.trim()){toast.error("Please enter email"); return;}                            
                            setStep(2);
                            setTimeout(() => {
                                passwordRef.current?.focus();
                            }, 0);
                        }
                    }} 
                    placeholder="name@example.com"
                    className="w-full h-14 rounded-xl border border-gray-300 pl-12 pr-4 outline-none focus:border-indigo-500
                        focus:ring-2 focus:ring-indigo-200" />

            </div>

            {/* Continue */}

            <button
                onClick={() => {
                    if (!email.trim()){toast.error("Please enter email"); return;}
                    setStep(2);
                    setTimeout(() => {
                        passwordRef.current?.focus();
                    }, 0);
                }}
                className="cursor-pointer w-full h-14 mt-6 rounded-xl bg-[#0B1324] text-white font-semibold
                    hover:bg-black transition">
                Continue
            </button>

            {/* Divider */}

            <div className="flex items-center gap-4 my-8">
                <div className="flex-1 h-px bg-gray-300" />
                <span className="text-sm text-gray-500">
                    OR CONTINUE WITH
                </span>
                <div className="flex-1 h-px bg-gray-300" />
            </div>

            {/* Google */}

            <button onClick={() => singInOAuth("google")}
                className="cursor-pointer w-full h-14 rounded-xl border border-gray-300 flex items-center justify-center gap-3 hover:bg-gray-50 transition">
                <img src="images/google.png" className="w-5 h-5" alt="Google" />
                Continue with Google
            </button>

            {/* Github */}

            <button onClick={() => singInOAuth("github")}
                className="cursor-pointer mt-4 w-full h-14 rounded-xl border border-gray-300 flex items-center justify-center gap-3 hover:bg-gray-50 transition" >
                <img src="images/github.png" className="w-5 h-5" alt="GitHub" />
                Continue with GitHub
            </button>

            {/* Signup */}

            <div className="text-center mt-8">

                <span className="text-gray-500">
                    Don't have an account?
                </span>

                <button
                    onClick={() => router.push("/signup")}
                    className="
                        cursor-pointer
                        ml-2
                        font-semibold
                        text-indigo-600
                    "
                >
                    Sign Up
                </button>

            </div>

        </>

    ) : (

        <>
            {/* Back */}

            <button 
            onClick= {() => {
                setStep(1);
                setTimeout(() => {
                        emailRef.current?.focus();
                    }, 0);
                }
            } 
            className="cursor-pointer text-sm text-indigo-600 mb-6">
                ← Back
            </button>

            {/* Email */}

            <div className="mb-6">

                <div className="font-semibold text-lg">
                    {email}
                </div>

                {/* <button
                    onClick={() => setStep(1)}
                    className="
                        cursor-pointer
                        text-sm
                        text-indigo-600
                        mt-1
                    "
                >
                    Change email
                </button> */}

            </div>

            {/* Password */}

            <div className="relative">

                <LockClosedIcon
                    className="absolute left-4 top-4 w-5 h-5 text-gray-400"
                />

                
                    <input
                        ref={passwordRef}
                        type={showPassword ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter") {
                                login();
                            }
                        }}
                        placeholder="Password"
                        className="
                            w-full
                            h-14
                            rounded-xl
                            border
                            border-gray-300
                            pl-12
                            pr-4
                            outline-none
                            focus:border-indigo-500
                            focus:ring-2
                            focus:ring-indigo-200
                        "
                    />
                    <button
                        type="button"
                        onClick={()=>setShowPassword(!showPassword)}
                        className="absolute right-4 top-4 text-sm cursor-pointer text-gray-300 hover:text-gray-500"
                    >
                        {showPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                    </button>
                

            </div>

            {/* Forgot Password */}

            <div className="flex justify-end mt-4">

                <button
                    onClick={() => router.push("/forgot-password")}
                    className="
                        cursor-pointer
                        text-sm
                        text-indigo-600
                    "
                >
                    Forgot Password?
                </button>

            </div>

            {/* Login */}

            <button
                onClick={login}
                className="
                    cursor-pointer
                    w-full
                    h-14
                    mt-6
                    rounded-xl
                    bg-[#0B1324]
                    text-white
                    font-semibold
                    hover:bg-black
                    transition
                "
            >
                Login
            </button>

            {/* Divider */}

            <div className="flex items-center gap-4 my-8">

                <div className="flex-1 h-px bg-gray-300" />

                <span className="text-sm text-gray-500">
                    OR CONTINUE WITH
                </span>

                <div className="flex-1 h-px bg-gray-300" />

            </div>

            {/* Google */}

            <button onClick={() => singInOAuth("google")}
                className="cursor-pointer w-full h-14 rounded-xl border border-gray-300 flex items-center justify-center gap-3 hover:bg-gray-50 transition">
                <img src="images/google.png" className="w-5 h-5" alt="Google" />
                Continue with Google
            </button>

            {/* Github */}

            <button onClick={() => singInOAuth("github")}
                className="cursor-pointer mt-4 w-full h-14 rounded-xl border border-gray-300 flex items-center justify-center gap-3 hover:bg-gray-50 transition">
                <img src="images/github.png" className="w-5 h-5" alt="GitHub" />
                Continue with GitHub
            </button>

        </>

    )}

</AuthLayout>   

  );
}