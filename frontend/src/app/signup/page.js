"use client";

import AuthLayout from "@/components/AuthLayout";
import { useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"
import { EnvelopeIcon, LockClosedIcon, EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";

export default function SignupPage() {

  const { setGlobalLoading } = useLoading();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const router = useRouter();

  const validatePassword = (password) => {
        const passwordRegex =
            /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&^#()_\-+=\[\]{}|\\:;"'<>,./~`])[A-Za-z\d@$!%*?&^#()_\-+=\[\]{}|\\:;"'<>,./~`]{8,}$/;

        return passwordRegex.test(password);
    };

  const passwordChecks = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[^A-Za-z0-9]/.test(password),
    };  

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

    if (!validatePassword(password)) {
        toast.error(
            "Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one number and one special character."
        );
        return;
    }

    try{

        setGlobalLoading(true);

        const { error } = await supabase.auth.signUp({

            email,
            password,
            options: {
                emailRedirectTo: `${process.env.NEXT_PUBLIC_APP_URL}`
            }

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
            icon="👤"
            title="Create Account"
            subtitle="Create your AI workspace account and start chatting."
        >
            {/* Email */}

            <div className="relative">

                <EnvelopeIcon className="w-5 h-5 absolute left-4 top-4 text-gray-400" />

                <input
                    type="email"
                    placeholder="Email Address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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

                <LockClosedIcon className="w-5 h-5 absolute left-4 top-4 text-gray-400" />

                <input
                    type={showPassword ? "text" : "password"}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
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
                <button
                    type="button"
                    onClick={()=>setShowPassword(!showPassword)}
                    className="absolute right-4 top-4 text-sm cursor-pointer text-gray-300 hover:text-gray-500"
                >
                    {showPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                </button>

            </div>

            {/* Confirm Password */}

            <div className="relative mt-5">

                <LockClosedIcon className="w-5 h-5 absolute left-4 top-4 text-gray-400" />

                <input
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="Confirm Password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
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
                <button
                    type="button"
                    onClick={()=>setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-4 text-sm cursor-pointer text-gray-300 hover:text-gray-500"
                >
                    {showConfirmPassword ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                </button>

            </div>

            {/* Password Hint */}

            <p className="mt-4 text-sm text-gray-500 leading-6">
                Password must contain at least
                <span className="font-semibold text-gray-700">
                    {" "}8 characters
                </span>
                , one uppercase letter, one lowercase letter,
                one number and one special character.
            </p>

            {/* <div className="mt-4 text-sm space-y-1">
                <p className={passwordChecks.length ? "text-green-600" : "text-gray-500"}>
                    ✓ At least 8 characters
                </p>

                <p className={passwordChecks.uppercase ? "text-green-600" : "text-gray-500"}>
                    ✓ One uppercase letter
                </p>

                <p className={passwordChecks.lowercase ? "text-green-600" : "text-gray-500"}>
                    ✓ One lowercase letter
                </p>

                <p className={passwordChecks.number ? "text-green-600" : "text-gray-500"}>
                    ✓ One number
                </p>

                <p className={passwordChecks.special ? "text-green-600" : "text-gray-500"}>
                    ✓ One special character
                </p>
            </div> */}

            {/* Button */}

            <button
                onClick={signup}
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
                Create Account
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

            {/* Login */}

            <div className="text-center mt-8">

                <span className="text-gray-500">
                    Already have an account?
                </span>

                <button
                    onClick={() => router.push("/login")}
                    className="
                        cursor-pointer
                        ml-2
                        font-semibold
                        text-black
                    "
                >
                    Login
                </button>

            </div>

        </AuthLayout>
  );
}