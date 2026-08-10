"use client";

import AuthLayout from "@/components/AuthLayout";
import { useState } from "react";
import toast from "react-hot-toast";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"
import { LockClosedIcon, EyeIcon, EyeSlashIcon  } from "@heroicons/react/24/outline";
import Link from "next/link";

export default function ResetPasswordPage() {

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { setGlobalLoading } = useLoading();
  
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

  const updatePassword = async () => {
    try 
    {
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

        //Validation
        if (!validatePassword(password)) {
            toast.error(
                "Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one number and one special character."
            );
            return;
        }

        setGlobalLoading(true);
        const { error } =
            await supabase.auth.updateUser({
            password
            });

        if (error) {

            toast.error(error.message);

            return;
        }

        toast.success(
            "Password updated successfully"
        );

        router.push("/login");
    }
    finally {
      setGlobalLoading(false);
    }
  };

  return (

    <AuthLayout
            icon="🔐"
            title="Reset Password"
            subtitle="Create a strong password for your account."
        >

            {/* New Password */}

            <div className="relative">

                <LockClosedIcon className="w-5 h-5 absolute left-4 top-4 text-gray-400" />

                <input
                    type={showPassword ? "text" : "password"}
                    placeholder="New Password"
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

            {/* Update Button */}

            <button
                onClick={updatePassword}
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
                Update Password
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