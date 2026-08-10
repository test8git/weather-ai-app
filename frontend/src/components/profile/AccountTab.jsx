"use client";

import { useState } from "react";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";

export default function AccountTab({
    currentPassword,
    setCurrentPassword,

    newPassword,
    setNewPassword,

    confirmPassword,
    setConfirmPassword
})
{
    const [showCurrent, setShowCurrent] = useState(false);
    const [showNew, setShowNew] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);

    return (

        <div className="space-y-6">

            <h3 className="text-xl font-semibold text-black">
                Change Password
            </h3>

            {/* Current Password */}

            <div>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Current Password
                </label>

                <div className="relative">

                    <input
                        type={showCurrent ? "text" : "password"}
                        value={currentPassword}
                        onChange={(e)=>setCurrentPassword(e.target.value)}
                        className="w-full h-12 border rounded-xl px-4 pr-16 outline-none"
                    />

                    <button
                        type="button"
                        onClick={()=>setShowCurrent(!showCurrent)}
                        className="absolute right-4 top-4 text-sm cursor-pointer text-gray-300 hover:text-gray-500"
                    >
                        {showCurrent ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                    </button>

                </div>

            </div>

            {/* New Password */}

            <div>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                    New Password
                </label>

                <div className="relative">

                    <input
                        type={showNew ? "text" : "password"}
                        value={newPassword}
                        onChange={(e)=>setNewPassword(e.target.value)}
                        className="w-full h-12 border rounded-xl px-4 pr-16 outline-none"
                    />

                    <button
                        type="button"
                        onClick={()=>setShowNew(!showNew)}
                        className="absolute right-4 top-4 text-sm cursor-pointer text-gray-300 hover:text-gray-500"
                    >
                        {showNew ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                    </button>

                </div>

            </div>

            {/* Confirm Password */}

            <div>

                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Confirm Password
                </label>

                <div className="relative">

                    <input
                        type={showConfirm ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(e)=>setConfirmPassword(e.target.value)}
                        className="w-full h-12 border rounded-xl px-4 pr-16 outline-none"
                    />

                    <button
                        type="button"
                        onClick={()=>setShowConfirm(!showConfirm)}
                        className="absolute right-4 top-4 text-sm cursor-pointer text-gray-300 hover:text-gray-500"
                    >
                        {showConfirm ? <EyeSlashIcon className="w-5 h-5" /> : <EyeIcon className="w-5 h-5" />}
                    </button>

                </div>

            </div>

            <p className="mt-4 text-sm text-gray-500 leading-6">
                Password must contain at least
                <span className="font-semibold text-gray-700">
                    {" "}8 characters
                </span>
                , one uppercase letter, one lowercase letter,
                one number and one special character.
            </p>

        </div>

    );

}