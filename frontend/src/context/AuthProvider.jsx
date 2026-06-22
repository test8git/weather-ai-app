"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState
} from "react";

import { supabase } from "@/lib/supabase";

const AuthContext = createContext();

export function AuthProvider({ children }) {

    const [user, setUser] = useState(undefined);
    const [loading, setLoading] = useState(true);

    useEffect(() => {

        const getUser = async () => {

        const {data: { user }} = await supabase.auth.getUser();
        
        // console.log("getUser user:", user);
        
        const {data: { session }} = await supabase.auth.getSession();

        // console.log("getSession:", session);

        setUser(user ?? null);

        setLoading(false);
        };

        getUser();

        const {data: { subscription }} = supabase.auth.onAuthStateChange(
                                                        (event, session) => {
                                                            
                                                            // console.log("EVENT:", event);
                                                            // console.log("SESSION:", session);
                                                            
                                                            setUser(session?.user ?? null);

                                                            setLoading(false);
                                                        });

        return () => subscription.unsubscribe();

    }, []);

    return (
        <AuthContext.Provider
        value={{
            user,
            loading
        }}
        >
        {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);