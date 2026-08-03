"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { supabase } from "@/lib/supabase";

export default function AuthCallback() {

    const router = useRouter();

    useEffect(() => {


        async function finishLogin() {

            const { data } = await supabase.auth.getSession();

            console.log("Session:", data.session);

            if (data.session) {

                toast.success("Redirecting to home...");

                window.location.href = "/";

            }

        }

        finishLogin();

        // const exchangeCode = async () => {

        //     const url = new URL(window.location.href);

        //     console.log("Current URL:", url);

        //     const code = url.searchParams.get("code");

        //     console.log("Code:", code);

        //     if (!code) {
        //         router.replace("/login");
        //         return;
        //     }

        //     const { data, error } = await supabase.auth.exchangeCodeForSession(code);

        //     console.log("Exchange Result:", data);
        //     console.log("Exchange Error:", error);

        //     if (error) {
        //         toast.error(error);
        //         router.replace("/login");
        //         return;
        //     }

        //     router.replace("/");

        // };

        // exchangeCode();

    }, []);

    return (

        <div className="flex h-screen items-center justify-center">

            <div className="text-lg font-semibold">
                Signing you in...
            </div>

        </div>

    );

}