"use client";

import { UserCircleIcon } from "@heroicons/react/24/solid";

import { useAuth } from "@/context/AuthProvider";
import { useUserProfile } from "@/context/UserProvider";

export default function ProfileTab({
    fullName,
    setFullName,
    email,
    avatarPreview,
    setAvatarPreview,
    avatarFile,
    setAvatarFile
})
{
    const { user } = useAuth();
    const { profile } = useUserProfile();

    return (

        <div className="space-y-8">

            {/* Avatar */}

            <div className="flex items-center gap-6">

                <div className="w-24 h-24 rounded-full bg-indigo-600 overflow-hidden flex items-center justify-center text-white text-4xl font-bold">

                    {avatarPreview ? (

                        <img
                            src={avatarPreview}
                            className="w-full h-full object-cover"
                        />

                    ) : (

                        fullName
                            .charAt(0)
                            .toUpperCase()

                    )}

                </div>

                <div>

                    <h3 className="text-lg font-semibold">
                        Photo
                    </h3>

                    <p className="text-gray-500 text-sm mb-3">
                        JPG, PNG
                    </p>

                    <label className="cursor-pointer px-4 py-2 rounded-xl bg-indigo-600 text-white">

                        Change Photo

                        <input
                            type="file"
                            accept="image/*"
                            className="hidden"

                            onChange={(e)=>{

                                const file = e.target.files?.[0];

                                if (!file) return;

                                setAvatarFile(file);

                                setAvatarPreview(
                                    URL.createObjectURL(file)
                                );

                            }}
                        />

                    </label>

                </div>

            </div>

            {/* Full Name */}

            <div>

                <label className="block text-sm font-medium text-gray-700 mb-2">

                    Full Name

                </label>

                <input
                    value={fullName}
                    onChange={(e)=>setFullName(e.target.value)}
                    className="w-full h-12 border rounded-xl px-4 outline-none"
                />

            </div>

            {/* Email */}

            <div>

                <label className="block text-sm font-medium text-gray-700 mb-2">

                    Email

                </label>

                <input
                    value={email}
                    readOnly
                    className="w-full h-12 border rounded-xl px-4 bg-gray-100 text-gray-600"
                />

            </div>

        </div>

    );

}