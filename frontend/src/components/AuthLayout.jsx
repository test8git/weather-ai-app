export default function AuthLayout({
    icon,
    title,
    subtitle,
    children,
    illustration = "/images/chat-with-ai.svg",
}) {
    return (
        <div className="min-h-[100dvh] bg-[#9AA3AF] flex items-center justify-center p-4 sm:p-6 lg:p-8">

            <div className="w-full max-w-md lg:max-w-7xl bg-white rounded-2xl shadow-2xl overflow-hidden grid lg:grid-cols-2">

                {/* LEFT PANEL */}

                <div className="flex items-center justify-center px-6 py-14 sm:px-10 sm:py-16 lg:px-20 lg:py-20">

                    <div className="w-full max-w-md">

                        {/* Icon */}

                        <div className="flex justify-center mb-8">

                            <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center text-2xl">

                                {icon}

                            </div>

                        </div>

                        {/* Heading */}

                        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-center text-gray-900">

                            {title}

                        </h1>

                        {/* Subtitle */}

                        <p className="text-center text-gray-500 mt-3 mb-10">

                            {subtitle}

                        </p>

                        {/* Page Content */}

                        {children}

                    </div>

                </div>

                {/* RIGHT PANEL */}

                <div className="hidden lg:flex items-center justify-center bg-[#EEF2F6]">

                    <img
                        src={illustration}
                        alt={title}
                        className="w-[80%] object-contain"
                    />

                </div>

            </div>

        </div>
    );
}