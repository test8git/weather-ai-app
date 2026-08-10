"use client";
import { useState, useRef, useEffect } from "react";
import {
    ChevronUpIcon,
    ChevronDownIcon,
    UserCircleIcon,
    Cog6ToothIcon,
    QuestionMarkCircleIcon,
    ArrowRightOnRectangleIcon
} from "@heroicons/react/24/outline";

import { useAuth } from "@/context/AuthProvider";
import { useUserProfile } from "@/context/UserProvider";
import ConnectZapierModal from "@/components/ConnectZapierModal";

export default function ProfileMenu({
    collapsed,
    onLogout,
    onProfile
})
{
    const { user } = useAuth();
    const { profile, refreshProfile } = useUserProfile();

    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef(null);

    //Zapier related states
    const [showZapierModal,setShowZapierModal]=useState(false);

    useEffect(() => {

        function handleClickOutside(event) {

            if (
                menuRef.current &&
                !menuRef.current.contains(event.target)
            ) {
                setMenuOpen(false);
            }

        }

        document.addEventListener("mousedown", handleClickOutside);

        return () =>
            document.removeEventListener(
                "mousedown",
                handleClickOutside
            );

    }, []);

    return (
        <>
        <div ref={menuRef} className="bg-white/5 rounded-2xl p-2 border border-white/10">

            <div
            onClick={() => {
                setMenuOpen(!menuOpen);
            }} 
            className={`cursor-pointer flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>

                <div className={`w-12  h-12 flex items-center justify-center text-lg font-bold ${!collapsed ? "rounded-full bg-indigo-600" : "" } `}>

                    {profile?.avatar_url ? (

                        <img
                            src={`${profile.avatar_url}?t=${Date.now()}`}
                            alt={(profile?.full_name || user?.email || "U").charAt(0).toUpperCase()}
                            className="w-full h-full object-cover rounded-full"
                        />

                    ) : (

                        <span className="text-lg font-bold text-white">
                            {(profile?.full_name || user?.email || "U")
                                .charAt(0)
                                .toUpperCase()}
                        </span>

                    )}

                </div>
                {!collapsed && (
                    <div className="flex-1 min-w-0">
                        <div className="text-sm text-gray-400 truncate">
                            {(profile?.full_name || user?.email || "")}
                        </div>

                    </div>
                )}

                {menuOpen && !collapsed && (

                    <div className="absolute bottom-16 right-0 mb-3 w-72 rounded-2xl bg-[#202123] border border-white/10 shadow-2xl overflow-hidden z-50" >
                        <div className="px-5 py-4 border-b border-white/10">
                            <div className="font-semibold text-white">
                                {profile?.full_name}
                            </div>
                            <div className="text-sm text-gray-400">
                                {user?.email}
                            </div>
                        </div>

                        {/* <button className="cursor-pointer w-full px-5 py-3 flex items-center gap-3 hover:bg-white/10 transition" 
                            onClick={()=>{
                                setMenuOpen(false);
                                onProfile();
                            }}
                        >
                            <UserCircleIcon className="w-5 h-5"/>
                            Profile
                        </button> */}

                        <button onClick={()=>setShowZapierModal(true)}
                            className="cursor-pointer w-full px-5 py-3 flex items-center gap-3 hover:bg-white/10 transition">
                            ⚡ {profile?.mcp_connected ? "Reconnect " : "Connect "} Zapier
                        </button>

                        {/* <button className="cursor-pointer w-full px-5 py-3 flex items-center gap-3 hover:bg-white/10 transition">
                            <Cog6ToothIcon className="w-5 h-5"/>
                            Settings
                        </button>

                        <button className="cursor-pointer w-full px-5 py-3 flex items-center gap-3 hover:bg-white/10 transition" >
                            <QuestionMarkCircleIcon className="w-5 h-5"/>
                            Help
                        </button> */}

                        <button
                            onClick={onLogout}
                            className="cursor-pointer w-full px-5 py-3 flex items-center gap-3 hover:bg-red-600 transition text-red-400 hover:text-white"
                        >
                            <ArrowRightOnRectangleIcon className="w-5 h-5"/>
                            Logout
                        </button>
                    </div>
                )}

            

                {!collapsed && (

                    // <button
                    //     onClick={onLogout}
                    //     className="mt-4 w-full bg-red-600 rounded-xl p-2"
                    // >
                    //     Logout
                    // </button>

                    <div className="ml-auto">

                        {menuOpen ? (

                            <ChevronUpIcon className="w-5 h-5 text-gray-400"/>

                        ) : (

                            <ChevronDownIcon className="w-5 h-5 text-gray-400"/>

                        )}

                    </div>

                )}
            </div>

        </div>
        
        <ConnectZapierModal profile={profile} open={showZapierModal} onClose={()=>setShowZapierModal(false)} onConnected={refreshProfile} />

        </>
    );
}