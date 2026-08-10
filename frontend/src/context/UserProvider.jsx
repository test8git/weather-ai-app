"use client";

import {
    createContext,
    useContext,
    useEffect,
    useState
} from "react";

import { supabase } from "@/lib/supabase";
import { useAuth } from "./AuthProvider";

const UserContext = createContext();

export function UserProvider({ children })
{
    const { user } = useAuth();

    const [profile, setProfile] = useState(null);

    const [loadingProfile, setLoadingProfile] = useState(true);

    const refreshProfile = async () =>
    {
        if (!user)
        {
            setProfile(null);
            setLoadingProfile(false);
            return;
        }

        setLoadingProfile(true);

        const { data, error } = await supabase
            .from("profiles")
            .select("*")
            .eq("id", user.id)
            .single();

        if (error)
        {
            console.error("Load Profile Error:", error);
            setProfile(null);
        }
        else
        {
            setProfile(data);
        }

        setLoadingProfile(false);
    };

    useEffect(() =>
    {        
        refreshProfile();

    }, [user]);

    return (
        <UserContext.Provider
            value={{
                profile,
                setProfile,
                loadingProfile,
                refreshProfile
            }}
        >
            {children}
        </UserContext.Provider>
    );
}

export const useUserProfile = () => useContext(UserContext);