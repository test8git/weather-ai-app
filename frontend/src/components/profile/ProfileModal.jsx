"use client";

import { useRef, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useLoading } from "@/context/LoadingContext"
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/context/AuthProvider";
import { useUserProfile } from "@/context/UserProvider";
import { uploadAvatar, updateProfile } from "@/lib/profileApi";
import ProfileTab from "./ProfileTab";
import AccountTab from "./AccountTab";

export default function ProfileModal({
    open,
    onClose
})
{
    const { setGlobalLoading } = useLoading();
    const [loadingLocal, setLoadingLocal] = useState(false);

    const [activeTab, setActiveTab] = useState("profile");

    const { user } = useAuth();
    const {profile, refreshProfile} = useUserProfile();
    
    const [fullName, setFullName] = useState("");
    const [avatarFile, setAvatarFile] = useState(null);
    const [avatarPreview, setAvatarPreview] = useState("");

    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    async function handleSave()
    {
        if(activeTab==="profile")
        {
            await saveProfile();
        }
        else
        {
            await changePassword();
        }
    }

    useEffect(() => {
        if (!profile) return;

        setFullName(profile.full_name || "");
        setAvatarPreview(profile.avatar_url || "");
        setAvatarFile(null);

    }, [profile]);

    //
    // Close with ESC
    //
    useEffect(() => {

        function handleKey(e)
        {
            if (e.key === "Escape")
            {
                onClose();
            }
        }

        if (open)
        {
            window.addEventListener("keydown", handleKey);
        }

        return () =>
            window.removeEventListener("keydown", handleKey);

    }, [open, onClose]);

    //
    // Don't render when closed
    //
    if (!open)
    {
        return null;
    }

    async function saveProfile()
    {
        try
        {
            setGlobalLoading(true);
            setLoadingLocal(true);

            let avatarUrl = avatarPreview;

            //
            // Upload new avatar
            //

            if (avatarFile)
            {
                avatarUrl = await uploadAvatar(user.id, avatarFile);

                setAvatarPreview(avatarUrl + "?t=" + Date.now());
            }

            //
            // Update profile
            //

            await updateProfile({id: user.id, full_name: fullName, avatar_url: avatarUrl});

            toast.success("Profile updated");

            //
            // Refresh UserProvider
            //
            await refreshProfile();

            onClose();

        }
        catch(err)
        {
            toast.error(err.message);
        }
        finally
        {
            setGlobalLoading(false);
            setLoadingLocal(false);
        }
    }

    const validatePassword = (password) => {
        const passwordRegex =
            /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&^#()_\-+=\[\]{}|\\:;"'<>,./~`])[A-Za-z\d@$!%*?&^#()_\-+=\[\]{}|\\:;"'<>,./~`]{8,}$/;

        return passwordRegex.test(password);
    };

    const changePassword = async () => {
        if (!currentPassword)
            return toast.error("Enter current password.");
        
        if (!newPassword)
            return toast.error("Enter new password.");

        if (newPassword !== confirmPassword)
            return toast.error("Passwords do not match.");

        if (newPassword.length < 8)
            return toast.error("Password must be at least 8 characters.");

        if (!validatePassword(newPassword)) {
            toast.error(
                "Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one number and one special character."
            );
            return;
        }        

        try {
            setGlobalLoading(true);
            setLoadingLocal(true);

            const { error: loginError } =
                await supabase.auth.signInWithPassword({

                    email: user.email,
                    password: currentPassword

                });

            if (loginError) {

                toast.error("Current password is incorrect.");

                return;
            }

            const { error } =
                await supabase.auth.updateUser({
                    password: newPassword
                });

            if (error)
                throw error;

            toast.success("Password updated.");

            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");

            onClose();

        }
        catch(err) {

            toast.error(err.message);

        }
        finally {

            setGlobalLoading(false);
            setLoadingLocal(false);

        }

    };

    return (

        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">

    <div className="bg-white rounded-2xl w-[700px] p-8 border border-white/10">

        {/* Header */}

        <h2 className="text-2xl font-bold text-black mb-6">
            My Profile
        </h2>

        {/* Tabs */}

        <div className="flex border-b mb-6">

            <button
                onClick={() => setActiveTab("profile")}
                className={`cursor-pointer px-5 py-3 font-medium border-b-2 transition
                ${
                    activeTab === "profile"
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-gray-500 hover:text-black"
                }`}
            >
                Profile
            </button>

            <button
                onClick={() => setActiveTab("account")}
                className={`cursor-pointer px-5 py-3 font-medium border-b-2 transition
                ${
                    activeTab === "account"
                        ? "border-indigo-600 text-indigo-600"
                        : "border-transparent text-gray-500 hover:text-black"
                }`}
            >
                Account
            </button>

        </div>

        {/* Body */}

        <div className="min-h-[350px] text-gray-900">

            {activeTab === "profile" && (
                <div>
                    <ProfileTab
                        fullName={fullName}
                        setFullName={setFullName}
                        email={user?.email || ""}
                        avatarPreview={avatarPreview}
                        setAvatarPreview={setAvatarPreview}
                        avatarFile={avatarFile}
                        setAvatarFile={setAvatarFile} />
                </div>
            )}

            {activeTab === "account" && (
                <div>
                    <AccountTab
                        currentPassword={currentPassword}
                        setCurrentPassword={setCurrentPassword}

                        newPassword={newPassword}
                        setNewPassword={setNewPassword}

                        confirmPassword={confirmPassword}
                        setConfirmPassword={setConfirmPassword}
                    />
                </div>
            )}

        </div>

        {/* Footer */}

        <div className="mt-8 flex justify-end gap-4">

            <button
                onClick={onClose}
                className="cursor-pointer rounded-xl border px-5 py-3 hover:bg-slate-100 text-black"
            >
                Cancel
            </button>

            <button onClick={handleSave}
                disabled={loadingLocal}
                className="cursor-pointer px-5 py-3 rounded-xl text-white bg-indigo-600"
            >
                {loadingLocal ? "Saving..." : "Save"}
            </button>

        </div>

    </div>

</div>

    );

}