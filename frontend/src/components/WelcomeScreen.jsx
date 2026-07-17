export default function WelcomeScreen({ askSuggestionToAI }) {

    return (
        <div className="flex-1 overflow-y-auto bg-slate-50">
            <div className="max-w-5xl mx-auto px-8 py-12">
                <div className="text-center">
                    {/* Logo */}

                    <div className="w-24 h-24 mx-auto rounded-3xl bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center text-5xl shadow-xl">

                        🤖

                    </div>

                    <h1 className="mt-8 text-5xl font-bold text-slate-800">
                        General AI Assistant
                    </h1>

                    <p className="mt-4 text-xl text-slate-500">
                        Your intelligent AI workspace
                    </p>

                    {/* Features */}

                    <div className="grid grid-cols-2 gap-5 mt-12">

                        <div className="bg-white rounded-2xl shadow p-6">

                            <div className="text-3xl mb-2">
                                💬
                            </div>

                            <h3 className="font-semibold text-lg">
                                Ask Anything
                            </h3>

                            <p className="text-slate-500 mt-2">
                                General knowledge, reasoning, research and brainstorming.
                            </p>

                        </div>

                        <div className="bg-white rounded-2xl shadow p-6">

                            <div className="text-3xl mb-2">
                                📄
                            </div>

                            <h3 className="font-semibold text-lg">
                                Analyze Documents
                            </h3>

                            <p className="text-slate-500 mt-2">
                                PDF, Word, Excel, PowerPoint and Email support.
                            </p>

                        </div>

                        <div className="bg-white rounded-2xl shadow p-6">

                            <div className="text-3xl mb-2">
                                💻
                            </div>

                            <h3 className="font-semibold text-lg">
                                Generate Code
                            </h3>

                            <p className="text-slate-500 mt-2">
                                PHP, Python, C#, SQL, JavaScript and more.
                            </p>

                        </div>

                        <div className="bg-white rounded-2xl shadow p-6">

                            <div className="text-3xl mb-2">
                                🌦
                            </div>

                            <h3 className="font-semibold text-lg">
                                Weather AI
                            </h3>

                            <p className="text-slate-500 mt-2">
                                Forecasts, charts and AI recommendations.
                            </p>

                        </div>

                    </div>

                    {/* Suggestions */}

                    <div className="mt-14">

                        <h3 className="text-lg font-semibold text-slate-700 mb-5">
                            Try one of these
                        </h3>

                        <div className="grid grid-cols-2 gap-4">

                            <button
                                className="rounded-xl bg-white shadow hover:shadow-lg transition p-4 text-left hover:border-blue-400 border"
                                onClick={() => askSuggestionToAI("Write a Python REST API using FastAPI")}
                            >
                                🚀 Write a Python REST API using FastAPI
                            </button>

                            <button
                                className="rounded-xl bg-white shadow hover:shadow-lg transition p-4 text-left hover:border-blue-400 border"
                                onClick={() => askSuggestionToAI("Explain Quantum Physics simply")}
                            >
                                ⚛ Explain Quantum Physics simply
                            </button>

                            <button
                                className="rounded-xl bg-white shadow hover:shadow-lg transition p-4 text-left hover:border-blue-400 border"
                                onClick={() => askSuggestionToAI("Apple current stock")}
                            >
                                📈 Apple current stock
                            </button>

                        </div>

                    </div>

                    <p className="mt-12 text-slate-400 text-sm">
                        Powered by Gemini • OpenAI • Claude • Groq • OpenRouter
                    </p>
                </div>
            </div>

        </div>

    );

}