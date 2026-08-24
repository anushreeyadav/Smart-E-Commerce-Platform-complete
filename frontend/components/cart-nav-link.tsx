"use client";

import Link from "next/link";

import { useCart } from "@/components/cart-provider";

export default function CartNavLink() {
  const { itemCount } = useCart();

  return (
    <Link
      href="/cart"
      className="relative text-sm font-medium text-slate-700 transition hover:text-slate-950"
    >
      <span className="inline-flex items-center gap-2">
        Cart
        <span
          className={`inline-flex min-w-6 items-center justify-center rounded-full px-2 py-0.5 text-xs font-bold transition ${
            itemCount > 0
              ? "bg-amber-400 text-slate-950 shadow-[0_0_0_4px_rgba(251,191,36,0.18)]"
              : "bg-slate-200 text-slate-600"
          }`}
        >
          {itemCount}
        </span>
      </span>
    </Link>
  );
}
