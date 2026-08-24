"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";

export default function AuthActionButton() {
  const router = useRouter();
  const { isLoggedIn, logout } = useAuth();

  const handleLogout = () => {
    logout();
    router.push("/customer-login");
    router.refresh();
  };

  if (isLoggedIn) {
    return (
      <button
        type="button"
        onClick={handleLogout}
        className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:bg-white hover:text-slate-950"
      >
        Logout
      </button>
    );
  }

  return (
    <Link
      href="/customer-login"
      prefetch={false}
      className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:bg-white hover:text-slate-950"
    >
      Login
    </Link>
  );
}
