"use client";

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

export default function AuthErrorPage() {
  const searchParams = useSearchParams();
  const error = searchParams.get('error');

  const getErrorMessage = (error: string | null) => {
    switch (error) {
      case 'Configuration':
        return 'There is a problem with the server configuration.';
      case 'AccessDenied':
        return 'Access denied. You do not have permission to sign in.';
      case 'Verification':
        return 'The verification token is invalid or has expired.';
      case 'OAuthSignin':
        return 'Error in OAuth sign in process.';
      case 'OAuthCallback':
        return 'Error in OAuth callback process.';
      case 'OAuthCreateAccount':
        return 'Could not create OAuth account.';
      case 'EmailCreateAccount':
        return 'Could not create email account.';
      case 'Callback':
        return 'Error in callback handler.';
      case 'OAuthAccountNotLinked':
        return 'OAuth account is not linked to any existing account.';
      case 'EmailSignin':
        return 'Error sending email sign in link.';
      case 'CredentialsSignin':
        return 'Invalid credentials provided.';
      default:
        return 'An authentication error occurred.';
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Authentication Error
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {getErrorMessage(error)}
          </p>
          {error && (
            <p className="mt-2 text-center text-xs text-gray-500">
              Error code: {error}
            </p>
          )}
        </div>
        <div>
          <Link
            href="/auth/signin"
            className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Try Again
          </Link>
          <Link
            href="/"
            className="mt-3 group relative w-full flex justify-center py-2 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}