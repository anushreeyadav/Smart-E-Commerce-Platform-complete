"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import CartNavLink from "@/components/cart-nav-link";
import NotificationBell from "@/components/notification-bell";
import {
  fetchOrder,
  isAuthenticated,
  onOrderStatusChanged,
  Order,
} from "@/lib/storefront";

const STATUS_STEPS = ["confirmed", "paid", "shipped", "delivered"];

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  confirmed: "bg-sky-100 text-sky-700",
  paid: "bg-emerald-100 text-emerald-700",
  shipped: "bg-amber-100 text-amber-700",
  delivered: "bg-teal-100 text-teal-700",
  cancelled: "bg-rose-100 text-rose-700",
};

const RETURN_STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-rose-100 text-rose-700",
  returned: "bg-sky-100 text-sky-700",
  refunded: "bg-cyan-100 text-cyan-700",
};

const RETURN_STATUS_LABELS: Record<string, string> = {
  pending: "Return Request Pending",
  approved: "Return Request Approved",
  rejected: "Return Request Rejected",
  returned: "Item Returned",
  refunded: "Refund Issued",
};

function StatusPill({
  status,
  styles = STATUS_STYLES,
}: {
  status: string;
  styles?: Record<string, string>;
}) {
  const style = styles[status] ?? "bg-slate-100 text-slate-600";

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${style}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function StatusTracker({ status }: { status: string }) {
  const currentIndex = STATUS_STEPS.indexOf(status);

  return (
    <div className="flex items-center gap-2">
      {STATUS_STEPS.map((step, index) => {
        const reached = currentIndex >= index;

        return (
          <div key={step} className="flex flex-1 items-center gap-2">
            <div className="flex flex-col items-center gap-2">
              <div
                className={`h-3 w-3 rounded-full border-2 transition ${
                  reached
                    ? "border-cyan-500 bg-cyan-500"
                    : "border-slate-300 bg-white"
                }`}
              />
              <span
                className={`text-[11px] font-semibold uppercase tracking-wide ${
                  reached ? "text-cyan-700" : "text-slate-400"
                }`}
              >
                {step}
              </span>
            </div>

            {index < STATUS_STEPS.length - 1 && (
              <div
                className={`h-0.5 flex-1 transition ${
                  currentIndex > index ? "bg-cyan-500" : "bg-slate-200"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function OrderDetailPage() {
  const params = useParams<{ id: string }>();
  const orderId = params.id;

  const [order, setOrder] = useState<Order | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [error, setError] = useState("");

  const loadOrder = async () => {
    setError("");

    try {
      const signedIn = await isAuthenticated();

      if (!signedIn) {
        setAuthenticated(false);
        return;
      }

      setAuthenticated(true);
      const data = await fetchOrder(orderId);
      setOrder(data);
    } catch (fetchError) {
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : "Unable to load this order."
      );
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadOrder();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  useEffect(() => {
    return onOrderStatusChanged((payload) => {
      if (payload.order_id !== orderId) {
        return;
      }

      setOrder((current) =>
        current
          ? {
              ...current,
              status: payload.new_status,
              payment_status: payload.payment_status ?? current.payment_status,
            }
          : current
      );
    });
  }, [orderId]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#f8fafc_45%,_#e0f2fe_100%)] text-slate-900">
      <header className="relative z-50 border-b border-white/70 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">
              Smart E-Commerce
            </h1>
            <p className="text-sm text-slate-500">Order details</p>
          </div>

          <nav className="flex items-center gap-6">
            <Link
              href="/orders"
              className="text-sm font-medium text-slate-700 transition hover:text-slate-950"
            >
              All Orders
            </Link>
            <CartNavLink />
            <NotificationBell />
            <AuthActionButton />
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-14">
        {error && (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700">
            {error}
          </div>
        )}

        {authenticated === false ? (
          <div className="rounded-3xl border border-white/70 bg-white/80 p-10 shadow-sm">
            <h3 className="text-2xl font-bold text-slate-950">
              Please log in to view this order
            </h3>
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
        ) : !order ? (
          <div className="rounded-3xl border border-white/70 bg-white/75 p-12 text-center text-slate-500 shadow-sm">
            Loading order...
          </div>
        ) : (
          <div className="space-y-6">
            <div className="rounded-3xl border border-white/70 bg-white/80 p-8 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                    Order
                  </p>
                  <p className="mt-1 font-mono text-sm text-slate-700">
                    {order.id}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Placed {new Date(order.created_at).toLocaleString()}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <StatusPill status={order.payment_status} />
                  <StatusPill status={order.status} />
                </div>
              </div>

              {order.status !== "cancelled" && (
                <div className="mt-8">
                  <StatusTracker status={order.status} />
                </div>
              )}
            </div>

            <div className="grid gap-6 lg:grid-cols-[1.5fr_0.9fr]">
              <div className="rounded-3xl border border-white/70 bg-white/85 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
                <h3 className="text-lg font-bold text-slate-950">Items</h3>

                <div className="mt-4 space-y-3">
                  {order.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
                    >
                      <div>
                        <p className="font-semibold text-slate-900">
                          {item.product_name ?? "Product"}
                        </p>
                        <p className="text-xs text-slate-500">
                          Qty {item.quantity} &middot;{" "}
                          {order.currency.toUpperCase()}{" "}
                          {Number(item.unit_price).toFixed(2)} each
                        </p>
                      </div>
                      <p className="font-semibold text-slate-900">
                        {order.currency.toUpperCase()}{" "}
                        {(Number(item.unit_price) * item.quantity).toFixed(2)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <aside className="h-fit rounded-3xl border border-slate-200 bg-slate-950 p-8 text-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
                  Summary
                </p>

                <div className="mt-6 space-y-4 text-sm text-slate-300">
                  <div className="flex items-center justify-between">
                    <span>Payment method</span>
                    <span className="capitalize">{order.payment_method}</span>
                  </div>
                  <div className="flex items-center justify-between border-t border-white/10 pt-4 text-base font-semibold text-white">
                    <span>Total</span>
                    <span>
                      {order.currency.toUpperCase()}{" "}
                      {Number(order.total_amount).toFixed(2)}
                    </span>
                  </div>
                </div>

                <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-300">
                  Tracking details will appear here once your order has
                  shipped.
                </div>
              </aside>
            </div>

            {order.return_request && (
              <div className="rounded-3xl border border-violet-200 bg-violet-50 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-lg font-bold text-slate-950">
                    Return Request
                  </h3>
                  <StatusPill
                    status={order.return_request.status}
                    styles={RETURN_STATUS_STYLES}
                  />
                </div>

                <p className="mt-2 text-sm font-semibold text-violet-800">
                  {RETURN_STATUS_LABELS[order.return_request.status] ??
                    `Return Request ${order.return_request.status}`}
                </p>

                <dl className="mt-4 space-y-3 text-sm text-slate-700">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-500">
                      Reason
                    </dt>
                    <dd className="mt-0.5">{order.return_request.reason}</dd>
                  </div>

                  {order.return_request.comments && (
                    <div>
                      <dt className="text-xs uppercase tracking-wide text-slate-500">
                        Your comments
                      </dt>
                      <dd className="mt-0.5">{order.return_request.comments}</dd>
                    </div>
                  )}

                  <div className="text-xs text-slate-500">
                    Submitted {formatDateTime(order.return_request.created_at)}
                  </div>

                  {order.return_request.reviewed_at && (
                    <div className="rounded-2xl bg-white/70 p-3 text-sm">
                      <p className="font-semibold text-slate-900">
                        {order.return_request.status === "rejected"
                          ? "Rejected"
                          : "Reviewed"}{" "}
                        {order.return_request.reviewed_by_name
                          ? `by ${order.return_request.reviewed_by_name} `
                          : ""}
                        on {formatDateTime(order.return_request.reviewed_at)}
                      </p>
                      {order.return_request.review_comment && (
                        <p className="mt-1 text-slate-600">
                          &ldquo;{order.return_request.review_comment}&rdquo;
                        </p>
                      )}
                    </div>
                  )}
                </dl>

                {order.return_request.history &&
                  order.return_request.history.length > 0 && (
                    <ul className="mt-4 space-y-1 border-t border-violet-200 pt-3 text-xs text-slate-600">
                      {order.return_request.history.map((entry) => (
                        <li key={entry.id}>
                          {entry.previous_status
                            ? `${entry.previous_status} → ${entry.new_status}`
                            : `submitted as ${entry.new_status}`}{" "}
                          &middot; {formatDateTime(entry.created_at)}
                          {entry.comment && (
                            <> — &ldquo;{entry.comment}&rdquo;</>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
