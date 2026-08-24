"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import {
  API_BASE_URL,
  saveCustomerTokens,
} from "@/lib/storefront";

const CREDENTIALS = {
  customer: {
    email: "customer@example.com",
    password: "Customer@12345",
    label: "Customer",
  },
  staff: {
    email: "staff@example.com",
    password: "Staff@12345",
    label: "Staff",
  },
  admin: {
    email: "admin@example.com",
    password: "Admin@12345",
    label: "Admin",
  },
} as const;

type RoleKey = keyof typeof CREDENTIALS;

export default function CustomerLoginPage() {
  const router = useRouter();
  const [selectedRole, setSelectedRole] = useState<RoleKey>("customer");
  const [email, setEmail] = useState<string>(CREDENTIALS.customer.email);
  const [password, setPassword] = useState<string>(
    CREDENTIALS.customer.password
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const applyRole = (role: RoleKey) => {
    setSelectedRole(role);
    setEmail(CREDENTIALS[role].email);
    setPassword(CREDENTIALS[role].password);
    setError("");
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(payload.detail ?? "Unable to log in.");
      }

      saveCustomerTokens(payload.access_token, payload.refresh_token);
      router.push("/products");
      router.refresh();
    } catch (loginError) {
      setError(
        loginError instanceof Error
          ? loginError.message
          : "Unable to log in."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#fef3c7,_#f8fafc_40%,_#e0f2fe_100%)] px-6 text-slate-900">
      <div className="grid w-full max-w-5xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[2rem] border border-white/70 bg-white/80 p-10 shadow-[0_30px_80px_rgba(15,23,42,0.10)] backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-700">
              Email Login
            </p>
            <AuthActionButton />
          </div>
          <h1 className="mt-4 text-4xl font-black tracking-tight text-slate-950">
            Sign in as customer, staff, or admin
          </h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
            Use the seeded FastAPI email/password flow. Pick a role and the
            matching demo credentials will be filled in for you.
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            {(Object.keys(CREDENTIALS) as RoleKey[]).map((role) => (
              <button
                key={role}
                type="button"
                onClick={() => applyRole(role)}
                className={`rounded-2xl border px-4 py-3 text-left transition ${
                  selectedRole === role
                    ? "border-slate-950 bg-slate-950 text-white"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-400"
                }`}
              >
                <p className="text-xs uppercase tracking-[0.18em] opacity-70">
                  {CREDENTIALS[role].label}
                </p>
                <p className="mt-1 text-sm font-semibold">
                  {CREDENTIALS[role].email}
                </p>
              </button>
            ))}
          </div>

          {error && (
            <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="rounded-full bg-slate-950 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <div className="mt-8 flex flex-wrap gap-4 text-sm">
            <Link
              href="/auth/login"
              prefetch={false}
              className="font-semibold text-cyan-700 transition hover:text-cyan-600"
            >
              Use Auth0 social login instead
            </Link>
            <Link
              href="/products"
              className="font-semibold text-slate-600 transition hover:text-slate-950"
            >
              Continue as guest
            </Link>
          </div>
        </section>

        <aside className="rounded-[2rem] border border-slate-200 bg-slate-950 p-10 text-white shadow-[0_30px_80px_rgba(15,23,42,0.16)]">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Demo Credentials
          </p>
          <div className="mt-6 space-y-5 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-semibold text-white">Customer</p>
              <p className="mt-2">Email: customer@example.com</p>
              <p>Password: Customer@12345</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-semibold text-white">Staff</p>
              <p className="mt-2">Email: staff@example.com</p>
              <p>Password: Staff@12345</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="font-semibold text-white">Admin</p>
              <p className="mt-2">Email: admin@example.com</p>
              <p>Password: Admin@12345</p>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
