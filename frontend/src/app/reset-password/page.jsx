"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { useLoading } from "@/context/LoadingContext"

export default function ResetPasswordPage() {

  const [password, setPassword] = useState("");
  const { setGlobalLoading } = useLoading();

  const router = useRouter();

  const updatePassword = async () => {
    try 
    {
      setGlobalLoading(true);
      const { error } =
        await supabase.auth.updateUser({
          password
        });

      if (error) {

        alert(error.message);

        return;
      }

      alert(
        "Password updated successfully"
      );

      router.push("/login");
    }
    finally {
      setGlobalLoading(false);
    }
  };

  return (

    <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-green-500 to-blue-500">

      <div className="bg-white p-8 rounded-3xl shadow-xl w-full max-w-md">

        <h1 className="text-3xl font-bold mb-6 text-center">
          Reset Password
        </h1>

        <input
          type="password"
          placeholder="New Password"
          className="w-full border p-3 rounded-xl mb-4"
          value={password}
          onChange={(e)=>setPassword(e.target.value)}
        />

        <button
          onClick={updatePassword}
          className="w-full bg-green-600 text-white p-3 rounded-xl"
        >
          Update Password
        </button>

      </div>

    </div>
  );
}