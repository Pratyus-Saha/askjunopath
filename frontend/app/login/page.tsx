"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error: signInError } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: "https://askjunopath-web.vercel.app/auth/callback" } });

      if (signInError) {
        throw signInError;
      }

      setSubmitted(true);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to send magic link. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-navy flex items-center justify-center p-4">
      <div className="bg-navy-raised border border-gold-soft rounded-md p-8 w-full max-w-md shadow-2xl relative overflow-hidden">
        {/* Subtle top border accent */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gold"></div>

        <div className="text-center mb-8">
          <h1 className="text-2xl font-serif text-ivory-warm mb-2">Sign in to AskJunoPath</h1>
          <p className="text-sm text-muted-dark">Enter your email to receive a sign-in link</p>
        </div>

        {submitted ? (
          <div className="text-center py-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-sage/20 text-sage mb-4">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-lg font-medium text-ivory-warm mb-2">Check your email</h2>
            <p className="text-sm text-muted-dark">
              We&apos;ve sent a sign-in link to <span className="text-ivory font-medium">{email}</span>.
            </p>
          </div>
        ) : (
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label htmlFor="email" className="sr-only">Email address</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-navy border border-gold-soft rounded px-4 py-3 text-ivory placeholder:text-muted-dark focus:outline-none focus:border-gold transition-colors"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-juno w-full"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Sending...
                </span>
              ) : (
                "Send magic link"
              )}
            </button>

            {error && (
              <div className="text-clay text-sm text-center bg-clay/10 py-2 px-3 rounded border border-clay/20">
                {error}
              </div>
            )}
          </form>
        )}
      </div>
    </main>
  );
}
