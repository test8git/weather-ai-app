export default function WelcomeScreen({ askSuggestionToAI }) {

    return (
        <div className="flex-1 overflow-y-auto bg-[#F8FAFC]">
            <div className="max-w-6xl mx-auto px-8 py-12">

                {/* Greeting */}
                <div className="text-center">

                    <div className="w-20 h-20 mx-auto rounded-2xl bg-indigo-100 flex items-center justify-center shadow">
                        🤖
                    </div>

                    <h1 className="mt-8 text-5xl font-bold text-gray-900">
                        Welcome Back
                    </h1>

                    <p className="mt-4 text-xl text-gray-500">
                        What would you like to do today?
                    </p>

                </div>

                {/* AI Capability Cards */}

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mt-14">

                    <div className="rounded-2xl bg-white border border-gray-200 p-6 hover:shadow-lg hover:border-indigo-500 transition cursor-pointer">

                        <div className="w-12 h-12 rounded-xl bg-indigo-100 flex items-center justify-center text-2xl">
                            💬
                        </div>

                        <h3 className="mt-5 text-lg font-semibold">
                            Ask Anything
                        </h3>

                        <p className="mt-2 text-sm text-gray-500 leading-6">
                            Research, brainstorming, writing, reasoning and everyday questions.
                        </p>

                    </div>

                    <div className="rounded-2xl bg-white border border-gray-200 p-6 hover:shadow-lg hover:border-indigo-500 transition cursor-pointer">

                        <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center text-2xl">
                            📄
                        </div>

                        <h3 className="mt-5 text-lg font-semibold">
                            Analyze Documents
                        </h3>

                        <p className="mt-2 text-sm text-gray-500 leading-6">
                            PDF, Word, Excel, PowerPoint and Email support.
                        </p>

                    </div>

                    <div className="rounded-2xl bg-white border border-gray-200 p-6 hover:shadow-lg hover:border-indigo-500 transition cursor-pointer">

                        <div className="w-12 h-12 rounded-xl bg-yellow-100 flex items-center justify-center text-2xl">
                            💻
                        </div>

                        <h3 className="mt-5 text-lg font-semibold">
                            Generate Code
                        </h3>

                        <p className="mt-2 text-sm text-gray-500 leading-6">
                            Python, JavaScript, SQL, C#, PHP, Java and more.
                        </p>

                    </div>

                    <div className="rounded-2xl bg-white border border-gray-200 p-6 hover:shadow-lg hover:border-indigo-500 transition cursor-pointer">

                        <div className="w-12 h-12 rounded-xl bg-pink-100 flex items-center justify-center text-2xl">
                            📊
                        </div>

                        <h3 className="mt-5 text-lg font-semibold">
                            Data Analysis
                        </h3>

                        <p className="mt-2 text-sm text-gray-500 leading-6">
                            Charts, CSV files, statistics, reports and dashboards.
                        </p>

                    </div>

                </div>

                {/* Suggested Prompts */}

                <div className="mt-16">

                    <div className="flex items-center justify-between">

                        <h2 className="text-2xl font-bold text-gray-900">
                            Suggested Prompts
                        </h2>

                        <span className="text-sm text-gray-500">
                            Click to start instantly
                        </span>

                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-8">

                        <button className="rounded-2xl border border-gray-200 bg-white p-5 text-left hover:border-indigo-500 hover:shadow-lg transition"
                        onClick={() => askSuggestionToAI("Write a Python REST API using FastAPI")}>

                            <div className="font-semibold text-gray-900">
                                🚀 Build a REST API using FastAPI
                            </div>

                            <p className="mt-2 text-sm text-gray-500">
                                Generate complete production-ready code.
                            </p>

                        </button>

                        <button className="rounded-2xl border border-gray-200 bg-white p-5 text-left hover:border-indigo-500 hover:shadow-lg transition"
                        onClick={() => askSuggestionToAI("Write a business communication professional email with polished wording.")}>

                            <div className="font-semibold text-gray-900">
                                ✍ Write a professional email
                            </div>

                            <p className="mt-2 text-sm text-gray-500">
                                Business communication with polished wording.
                            </p>

                        </button>

                        <button className="rounded-2xl border border-gray-200 bg-white p-5 text-left hover:border-indigo-500 hover:shadow-lg transition"
                        onClick={() => askSuggestionToAI("Explain Quantum Physics simply")}>

                            <div className="font-semibold text-gray-900">
                                ⚛ Explain Quantum Physics simply
                            </div>

                            <p className="mt-2 text-sm text-gray-500">
                                Science knowledge with AI insights.
                            </p>

                        </button>

                        <button className="rounded-2xl border border-gray-200 bg-white p-5 text-left hover:border-indigo-500 hover:shadow-lg transition"
                        onClick={() => askSuggestionToAI("Explain today's stock market")}>

                            <div className="font-semibold text-gray-900">
                                📈 Explain today's stock market
                            </div>

                            <p className="mt-2 text-sm text-gray-500">
                                Market trends with AI insights.
                            </p>

                        </button>

                    </div>

                </div>

                {/* Footer */}

                <div className="mt-20 text-center">

                    <p className="text-sm text-gray-400">
                        Powered by OpenAI • Gemini • Claude • Groq • OpenRouter
                    </p>

                </div>

            </div>
        </div>

    );

}