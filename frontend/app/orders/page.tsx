"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import CartNavLink from "@/components/cart-nav-link";
import NotificationBell from "@/components/notification-bell";
import {
  fetchMyOrders,
  isAuthenticated,
  onOrderStatusChanged,
  Order,
} from "@/lib/storefront";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  confirmed: "bg-sky-100 text-sky-700",
  paid: "bg-emerald-100 text-emerald-700",
  shipped: "bg-amber-100 text-amber-700",
  delivered: "bg-teal-100 text-teal-700",
  cancelled: "bg-rose-100 text-rose-700",
};

function StatusPill({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600";

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${style}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [error, setError] = useState("");

  const loadOrders = async () => {
    setError("");

    try {
      const signedIn = await isAuthenticated();

      if (!signedIn) {
        setAuthenticated(false);
        setOrders(null);
        return;
      }

      setAuthenticated(true);
      const data = await fetchMyOrders();
      setOrders(data);
    } catch (fetchError) {
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : "Unable to load your orders."
      );
      setOrders(null);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadOrders();
  }, []);

  useEffect(() => {
    return onOrderStatusChanged((payload) => {
      setOrders((current) =>
        current
          ? current.map((order) =>
              order.id === payload.order_id
                ? {
                    ...order,
                    status: payload.new_status,
                    payment_status:
                      payload.payment_status ?? order.payment_status,
                  }
                : order
            )
          : current
      );
    });
  }, []);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#f8fafc_45%,_#e0f2fe_100%)] text-slate-900">
      <header className="border-b border-white/70 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">
              Smart E-Commerce
            </h1>
            <p className="text-sm text-slate-500">Track your orders</p>
          </div>

          <nav className="flex items-center gap-6">
            <Link
              href="/"
              className="text-sm font-medium text-slate-700 transition hover:text-slate-950"
            >
              Home
            </Link>
            <Link
              href="/products"
              className="text-sm font-medium text-slate-700 transition hover:text-slate-950"
            >
              Products
            </Link>
            <CartNavLink />
            <NotificationBell />
            <AuthActionButton />
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-5xl px-6 py-14">
        <div className="mb-8 rounded-3xl border border-white/70 bg-white/80 p-8 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-700">
            Order History
          </p>
          <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-950">
            Your orders, live-updated.
          </h2>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            Status here updates in real time as your order moves from
            confirmed to paid, shipped, and delivered — no refresh needed.
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700">
            {error}
          </div>
        )}

        {authenticated === false ? (
          <div className="rounded-3xl border border-white/70 bg-white/80 p-10 shadow-sm">
            <h3 className="text-2xl font-bold text-slate-950">
              Please log in to view your orders
            </h3>
            <p className="mt-3 max-w-xl text-slate-600">
              Your order history is tied to your account.
            </p>
            <div className="mt-8">
              <Link
                href="/customer-login"
                prefetch={false}
                className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Log in
              </Link>
            </div>
          </div>
        ) : orders === null ? (
          <div className="rounded-3xl border border-white/70 bg-white/75 p-12 text-center text-slate-500 shadow-sm">
            Loading orders...
          </div>
        ) : orders.length === 0 ? (
          <div className="rounded-3xl border border-white/70 bg-white/80 p-10 shadow-sm">
            <h3 className="text-2xl font-bold text-slate-950">
              No orders yet
            </h3>
            <p className="mt-3 max-w-xl text-slate-600">
              Once you check out, your orders will show up here.
            </p>
            <div className="mt-8">
              <Link
                href="/products"
                prefetch={false}
                className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
              >
                Browse Products
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="block rounded-3xl border border-white/70 bg-white/85 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.06)] transition hover:border-cyan-200 hover:shadow-[0_20px_60px_rgba(8,145,178,0.12)]"
              >
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                      Order
                    </p>
                    <p className="mt-1 font-mono text-sm text-slate-700">
                      {order.id}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {new Date(order.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <StatusPill status={order.payment_status} />
                    <StatusPill status={order.status} />
                  </div>

                  <div className="text-right">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                      Total
                    </p>
                    <p className="text-lg font-black text-slate-950">
                      {order.currency.toUpperCase()}{" "}
                      {Number(order.total_amount).toFixed(2)}
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
