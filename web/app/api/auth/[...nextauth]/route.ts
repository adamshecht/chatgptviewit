import NextAuth from "next-auth"
import Auth0Provider from "next-auth/providers/auth0"
import type { NextAuthOptions } from "next-auth"

export const authOptions: NextAuthOptions = {
  providers: [
    Auth0Provider({
      clientId: process.env.AUTH0_CLIENT_ID!,
      clientSecret: process.env.AUTH0_CLIENT_SECRET!,
      issuer: process.env.AUTH0_ISSUER!,
      authorization: {
        params: {
          scope: 'openid profile email',
          prompt: 'login',
        },
      },
    })
  ],
  callbacks: {
    async jwt({ token, account, profile, user }) {
      // Persist the OAuth access_token and user profile to the token right after signin
      if (account) {
        token.accessToken = account.access_token
        token.idToken = account.id_token
        // Extract custom claims from id_token if available
        if (account.id_token) {
          try {
            // Decode the JWT to get custom claims (without verification for now)
            const base64Url = account.id_token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
              return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            const claims = JSON.parse(jsonPayload);
            token.company_id = claims.company_id || claims['https://brightstone.ca/company_id'];
            token.role = claims.role || claims['https://brightstone.ca/role'] || 'analyst';
          } catch (e) {
            console.error('Failed to decode JWT:', e);
          }
        }
      }
      if (user) {
        token.email = user.email;
        token.name = user.name;
      }
      return token
    },
    async session({ session, token }) {
      // Send properties to the client
      session.accessToken = token.accessToken as string
      session.user = {
        ...session.user,
        id: token.sub!,
        email: token.email as string,
        name: token.name as string,
        // @ts-ignore
        company_id: token.company_id || 'default',
        // @ts-ignore
        role: token.role || 'analyst',
      }
      return session
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  session: {
    strategy: 'jwt',
  },
}

const handler = NextAuth(authOptions)

export { handler as GET, handler as POST }