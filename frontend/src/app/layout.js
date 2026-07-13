import { Toaster } from "react-hot-toast";
import { AuthProvider } from "@/context/AuthProvider";
import { LoadingProvider } from "@/context/LoadingContext"
import GlobalLoader from "@/components/GlobalLoader"
import { Geist, Geist_Mono } from "next/font/google";
import { ConversationProvider} from "@/context/ConversationProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata = {
  title: "General AI Assistant",
  description: "General AI Assistant",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <ConversationProvider>
            <LoadingProvider>
              <GlobalLoader />
              {children}              
            </LoadingProvider>
          </ConversationProvider>
        </AuthProvider>
        <Toaster position="bottom-right" reverseOrder={false} 
                 toastOptions={{
                    duration: 2500, 
                    style: {borderRadius: "12px", background: "#333", color: "#fff"},
                    success: {
                      style: {background: "#16a34a", color: "#fff",},
                    },
                    error: {
                      style: {background: "#dc2626", color: "#fff",},
                    },
                  }} />
      </body>
    </html>
  );
}
