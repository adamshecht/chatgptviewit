"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loader2 } from "lucide-react";

export default function HomePage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/alerts");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-center min-h-screen">
            <div className="text-center">
              <h1 className="text-5xl font-bold text-gray-900 mb-4">
                CityScrape.ai
              </h1>
              <p className="text-xl text-gray-600 mb-8">
                AI-Powered Municipal Intelligence Platform
              </p>
              <p className="text-lg text-gray-500 mb-12 max-w-2xl mx-auto">
                Monitor municipal documents that impact your properties. 
                Get real-time alerts when planning decisions affect your developments.
              </p>
              <a
                href="/api/auth/signin"
                className="inline-block px-8 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                Sign In to Get Started
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}