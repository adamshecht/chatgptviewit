"use client";

import Link from "next/link";
import { useSession, signIn, signOut } from "next-auth/react";
import { usePathname } from "next/navigation";
import { Bell, FileText, Building, Settings, LogOut, User } from "lucide-react";

export function Navigation() {
  const { data: session, status } = useSession();
  const pathname = usePathname();

  const isActive = (path: string) => pathname === path;

  if (status === "loading") {
    return (
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-xl font-semibold">CityScrape</span>
            </div>
          </div>
        </div>
      </nav>
    );
  }

  if (!session) {
    return (
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <span className="text-xl font-semibold">CityScrape</span>
            </div>
            <div className="flex items-center">
              <button
                onClick={() => signIn("auth0")}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
              >
                Sign In
              </button>
            </div>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="bg-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <span className="text-xl font-semibold">CityScrape</span>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link
                href="/alerts"
                className={`${
                  isActive("/alerts")
                    ? "border-blue-500 text-gray-900"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <Bell className="w-4 h-4 mr-2" />
                Alerts
              </Link>
              <Link
                href="/properties"
                className={`${
                  isActive("/properties")
                    ? "border-blue-500 text-gray-900"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <Building className="w-4 h-4 mr-2" />
                Properties
              </Link>
              <Link
                href="/documents"
                className={`${
                  isActive("/documents")
                    ? "border-blue-500 text-gray-900"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <FileText className="w-4 h-4 mr-2" />
                Documents
              </Link>
              {session.user?.role === "admin" && (
                <Link
                  href="/settings"
                  className={`${
                    isActive("/settings")
                      ? "border-blue-500 text-gray-900"
                      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center text-sm text-gray-700">
              <User className="w-4 h-4 mr-2" />
              {session.user?.email}
            </div>
            <button
              onClick={() => signOut()}
              className="text-gray-500 hover:text-gray-700 flex items-center"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}