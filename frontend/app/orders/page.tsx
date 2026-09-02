"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import CartNavLink from "@/components/cart-nav-link";
import NotificationBell from "@/components/notification-bell";
import {
  approveReturnRequest,
  fetchAdminOrders,
  fetchCurrentUser,
  fetchMyOrders,
  fetchOrder,
  initiateReturnRefund,
  isAuthenticated,
  onOrderStatusChanged,
  Order,
  rejectReturnRequest,
  submitReturnRequest,
  syncOrderPayment,
  updateOrderStatus,
} from "@/lib/storefront";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-100 text-slate-600",
  confirmed: "bg-sky-100 text-sky-700",
  paid: "bg-emerald-100 text-emerald-700",
  shipped: "bg-amber-100 text-amber-700",
  out_for_delivery: "bg-orange-100 text-orange-700",
  delivered: "bg-teal-100 text-teal-700",
  return_requested: "bg-violet-100 text-violet-700",
  cancelled: "bg-rose-100 text-rose-700",
};

const RETURN_STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  rejected: "bg-rose-100 text-rose-700",
  returned: "bg-sky-100 text-sky-700",
  refunded: "bg-cyan-100 text-cyan-700",
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

// ---------------------------------------------------------------------------
// Customer view: a signed-in customer's own order history. Unchanged from
// the original /orders page other than being moved into this component.
// ---------------------------------------------------------------------------

function CustomerOrdersView() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [returnOrder, setReturnOrder] = useState<Order | null>(null);
  const [returnReason, setReturnReason] = useState("");
  const [returnComments, setReturnComments] = useState("");
  const [submittingReturn, setSubmittingReturn] = useState(false);

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

  const closeReturnForm = () => {
    setReturnOrder(null);
    setReturnReason("");
    setReturnComments("");
  };

  const submitReturn = async () => {
    if (!returnOrder || !returnReason.trim()) return;

    setSubmittingReturn(true);
    setError("");
    try {
      const returnRequest = await submitReturnRequest(returnOrder.id, {
        reason: returnReason.trim(),
        comment: returnComments.trim() || undefined,
      });
      setOrders((current) =>
        current
          ? current.map((order) =>
              order.id === returnOrder.id
                ? { ...order, return_request: returnRequest, return_eligible: false }
                : order
            )
          : current
      );
      closeReturnForm();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Unable to submit your return request."
      );
    } finally {
      setSubmittingReturn(false);
    }
  };

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
      <header className="relative z-50 border-b border-white/70 bg-white/75 backdrop-blur-xl">
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
              <div
                key={order.id}
                className="rounded-3xl border border-white/70 bg-white/85 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.06)] transition hover:border-cyan-200 hover:shadow-[0_20px_60px_rgba(8,145,178,0.12)]"
              >
                <Link
                  href={`/orders/${order.id}`}
                  className="block rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400"
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

                <div className="mt-5">
                  {order.return_request ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Return request:
                      </span>
                      <StatusPill
                        status={order.return_request.status}
                        styles={RETURN_STATUS_STYLES}
                      />
                      {order.return_request.review_comment && (
                        <span className="text-xs text-slate-500">
                          &ldquo;{order.return_request.review_comment}&rdquo;
                        </span>
                      )}
                    </div>
                  ) : order.return_eligible ? (
                    <button
                      type="button"
                      onClick={() => setReturnOrder(order)}
                      className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
                    >
                      Request Return
                    </button>
                  ) : order.status === "delivered" ? (
                    <span className="text-sm font-medium text-slate-500">
                      Return Window Expired
                    </span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {returnOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/45 px-6">
          <div className="w-full max-w-lg rounded-3xl bg-white p-7 shadow-2xl">
            <h3 className="text-2xl font-bold text-slate-950">Request a return</h3>
            <p className="mt-2 text-sm text-slate-600">
              Tell us why you would like to return order {returnOrder.id}.
            </p>
            <label className="mt-6 block text-sm font-semibold text-slate-800">
              Return reason
              <input
                value={returnReason}
                onChange={(event) => setReturnReason(event.target.value)}
                maxLength={500}
                required
                className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:border-cyan-500"
              />
            </label>
            <label className="mt-4 block text-sm font-semibold text-slate-800">
              Comments <span className="font-normal text-slate-500">(optional)</span>
              <textarea
                value={returnComments}
                onChange={(event) => setReturnComments(event.target.value)}
                maxLength={5000}
                rows={4}
                className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 text-slate-900 outline-none focus:border-cyan-500"
              />
            </label>
            <div className="mt-6 flex justify-end gap-3">
              <button type="button" onClick={closeReturnForm} disabled={submittingReturn} className="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50">
                Cancel
              </button>
              <button type="button" onClick={() => void submitReturn()} disabled={!returnReason.trim() || submittingReturn} className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50">
                {submittingReturn ? "Submitting..." : "Submit Return Request"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Admin/Staff view: the order-management dashboard. Rendered instead of
// CustomerOrdersView on this same /orders route when the signed-in user's
// role is admin or staff.
// ---------------------------------------------------------------------------

const PAGE_SIZE = 20;

const ORDER_STATUS_FILTERS = [
  "pending",
  "confirmed",
  "paid",
  "shipped",
  "out_for_delivery",
  "delivered",
  "return_requested",
  "cancelled",
];

// Mirrors ALLOWED_STATUS_TRANSITIONS in fastapi_backend/app/services/order_service.py.
// return_requested is intentionally excluded: that transition only happens
// when a customer submits a return request, never via manual admin action.
// "paid" is also excluded here on purpose: an order can only become paid
// through an actual verified Stripe payment (webhook or "Confirm Payment"),
// never a manual click - the backend rejects a manual attempt to set it too.
const NEXT_STATUSES: Record<string, string[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["cancelled"],
  paid: ["shipped", "cancelled"],
  shipped: ["out_for_delivery", "delivered"],
  out_for_delivery: ["delivered"],
  delivered: [],
  return_requested: [],
  cancelled: [],
};

function formatDateTime(value?: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

function formatMoney(order: Order) {
  return `${order.currency.toUpperCase()} ${Number(order.total_amount).toFixed(2)}`;
}

function AdminOrdersView() {
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");

  const [statusFilter, setStatusFilter] = useState("");
  const [paymentStatusFilter, setPaymentStatusFilter] = useState("");
  const [returnStatusFilter, setReturnStatusFilter] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const [banner, setBanner] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [statusActionLoading, setStatusActionLoading] = useState(false);
  const [statusDialogError, setStatusDialogError] = useState("");

  const [returnDialog, setReturnDialog] = useState<"approve" | "reject" | "refund" | null>(null);
  const [returnComment, setReturnComment] = useState("");
  const [returnActionLoading, setReturnActionLoading] = useState(false);
  const [returnDialogError, setReturnDialogError] = useState("");

  const [confirmPaymentLoading, setConfirmPaymentLoading] = useState(false);
  const [confirmPaymentResult, setConfirmPaymentResult] = useState<{
    type: "success" | "info" | "error";
    text: string;
  } | null>(null);

  const loadOrders = async () => {
    setListLoading(true);
    setListError("");
    try {
      const data = await fetchAdminOrders({
        status: statusFilter || undefined,
        paymentStatus: paymentStatusFilter || undefined,
        returnStatus: returnStatusFilter || undefined,
        search: search || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      setOrders(data.items);
      setTotal(data.total);
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Unable to load orders.");
      setOrders(null);
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadOrders();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, paymentStatusFilter, returnStatusFilter, search, page]);

  const openOrder = async (orderId: string) => {
    setSelectedOrderId(orderId);
    setSelectedOrder(null);
    setDetailError("");
    setDetailLoading(true);
    setConfirmPaymentResult(null);
    try {
      const order = await fetchOrder(orderId);
      setSelectedOrder(order);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "Unable to load order details.");
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelectedOrderId(null);
    setSelectedOrder(null);
    setPendingStatus(null);
    setStatusDialogError("");
    setReturnDialog(null);
    setReturnComment("");
    setReturnDialogError("");
    setConfirmPaymentResult(null);
  };

  const refreshAfterMutation = async (updatedOrder?: Order) => {
    if (updatedOrder) {
      setSelectedOrder(updatedOrder);
    } else if (selectedOrderId) {
      try {
        setSelectedOrder(await fetchOrder(selectedOrderId));
      } catch {
        // detail refresh failing shouldn't block the list refresh below
      }
    }
    void loadOrders();
  };

  const confirmStatusChange = async () => {
    if (!selectedOrderId || !pendingStatus) return;
    setStatusActionLoading(true);
    setStatusDialogError("");
    try {
      const updated = await updateOrderStatus(selectedOrderId, pendingStatus);
      setBanner({ type: "success", text: `Order status updated to "${pendingStatus.replace(/_/g, " ")}".` });
      setPendingStatus(null);
      await refreshAfterMutation(updated);
    } catch (err) {
      // Shown inline in the confirmation dialog itself - it sits above the
      // order-detail modal, so a banner on the page underneath would be
      // invisible until both modals are closed.
      setStatusDialogError(
        err instanceof Error ? err.message : "Unable to update order status."
      );
    } finally {
      setStatusActionLoading(false);
    }
  };

  const confirmReturnDecision = async () => {
    if (!selectedOrderId || !returnDialog) return;
    if (returnDialog === "reject" && !returnComment.trim()) {
      setReturnDialogError("A reason is required to reject a return request.");
      return;
    }
    if (returnDialog === "refund" && !selectedOrder?.return_request) return;

    setReturnActionLoading(true);
    setReturnDialogError("");
    try {
      if (returnDialog === "approve") {
        await approveReturnRequest(selectedOrderId, returnComment.trim() || undefined);
        setBanner({ type: "success", text: "Return request approved." });
      } else if (returnDialog === "reject") {
        await rejectReturnRequest(selectedOrderId, returnComment.trim());
        setBanner({ type: "success", text: "Return request rejected." });
      } else {
        await initiateReturnRefund(selectedOrder!.return_request!.id, returnComment.trim() || undefined);
        setBanner({ type: "success", text: "Refund initiated — the customer's payment has been refunded." });
      }
      setReturnDialog(null);
      setReturnComment("");
      await refreshAfterMutation();
    } catch (err) {
      // Shown inline (see confirmStatusChange above) so a failed refund/
      // approve/reject is actually visible instead of silently appearing to
      // do nothing behind the still-open confirmation dialog.
      setReturnDialogError(
        err instanceof Error ? err.message : "Unable to process the return request."
      );
    } finally {
      setReturnActionLoading(false);
    }
  };

  const handleConfirmPayment = async () => {
    if (!selectedOrderId) return;
    setConfirmPaymentLoading(true);
    setConfirmPaymentResult(null);
    try {
      const result = await syncOrderPayment(selectedOrderId);
      if (result.verified_state === "paid") {
        setConfirmPaymentResult({
          type: "success",
          text: "Stripe confirmed this payment — the order is now marked as Paid.",
        });
        setBanner({ type: "success", text: "Payment confirmed with Stripe." });
      } else if (result.verified_state === "already_settled") {
        setConfirmPaymentResult({ type: "info", text: "This payment was already confirmed." });
      } else if (result.verified_state === "failed") {
        setConfirmPaymentResult({
          type: "error",
          text: "Stripe reports this payment failed, was cancelled, or was never completed. It has not been marked as paid.",
        });
      } else {
        setConfirmPaymentResult({
          type: "info",
          text: "Stripe has not confirmed this payment yet — the customer may not have finished checkout.",
        });
      }
      await refreshAfterMutation();
    } catch (err) {
      setConfirmPaymentResult({
        type: "error",
        text: err instanceof Error ? err.message : "Unable to verify this payment with Stripe.",
      });
    } finally {
      setConfirmPaymentLoading(false);
    }
  };

  useEffect(() => {
    if (!banner) return;
    const timer = setTimeout(() => setBanner(null), 5000);
    return () => clearTimeout(timer);
  }, [banner]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#f8fafc_45%,_#e0f2fe_100%)] text-slate-900">
      <header className="relative z-50 border-b border-white/70 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">
              Smart E-Commerce
            </h1>
            <p className="text-sm text-slate-500">Order Management</p>
          </div>

          <nav className="flex items-center gap-6">
            <Link href="/" className="text-sm font-medium text-slate-700 transition hover:text-slate-950">
              Home
            </Link>
            <Link href="/products" className="text-sm font-medium text-slate-700 transition hover:text-slate-950">
              Products
            </Link>
            <NotificationBell />
            <AuthActionButton />
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-6 rounded-3xl border border-white/70 bg-white/80 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="md:col-span-2">
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Search
              </label>
              <div className="flex gap-2">
                <input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      setPage(1);
                      setSearch(searchInput);
                    }
                  }}
                  placeholder="Order ID, customer name, or email"
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500"
                />
                <button
                  type="button"
                  onClick={() => {
                    setPage(1);
                    setSearch(searchInput);
                  }}
                  className="rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                >
                  Search
                </button>
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Order status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setPage(1);
                  setStatusFilter(e.target.value);
                }}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500"
              >
                <option value="">All statuses</option>
                {ORDER_STATUS_FILTERS.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Payment status
              </label>
              <select
                value={paymentStatusFilter}
                onChange={(e) => {
                  setPage(1);
                  setPaymentStatusFilter(e.target.value);
                }}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500"
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                Return status
              </label>
              <select
                value={returnStatusFilter}
                onChange={(e) => {
                  setPage(1);
                  setReturnStatusFilter(e.target.value);
                }}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500"
              >
                <option value="">Any</option>
                <option value="none">No return request</option>
                <option value="pending">Pending review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="returned">Returned</option>
                <option value="refunded">Refunded</option>
              </select>
            </div>
          </div>
        </div>

        {banner && (
          <div
            className={`mb-6 rounded-2xl border px-5 py-4 ${
              banner.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-rose-200 bg-rose-50 text-rose-700"
            }`}
          >
            {banner.text}
          </div>
        )}

        {listError && (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700">
            {listError}
          </div>
        )}

        <div className="overflow-hidden rounded-3xl border border-white/70 bg-white/85 shadow-[0_20px_60px_rgba(15,23,42,0.06)]">
          {listLoading ? (
            <div className="p-12 text-center text-slate-500">Loading orders...</div>
          ) : !orders || orders.length === 0 ? (
            <div className="p-12 text-center text-slate-500">No orders match these filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Order</th>
                    <th className="px-4 py-3">Customer</th>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Total</th>
                    <th className="px-4 py-3">Payment</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Return</th>
                    <th className="px-4 py-3">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {orders.map((order) => (
                    <tr
                      key={order.id}
                      onClick={() => void openOrder(order.id)}
                      className="cursor-pointer transition hover:bg-cyan-50/60"
                    >
                      <td className="px-4 py-3 font-mono text-xs text-slate-700">
                        {order.id.slice(0, 8)}…
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">
                          {order.customer_name ?? "—"}
                        </div>
                        <div className="text-xs text-slate-500">{order.customer_email}</div>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{formatDateTime(order.created_at)}</td>
                      <td className="px-4 py-3 font-semibold text-slate-900">{formatMoney(order)}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-semibold uppercase text-slate-600">
                          {order.payment_status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill status={order.status} />
                      </td>
                      <td className="px-4 py-3">
                        {order.return_request ? (
                          <StatusPill
                            status={order.return_request.status}
                            styles={RETURN_STATUS_STYLES}
                          />
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {formatDateTime(order.updated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6 flex items-center justify-between text-sm text-slate-600">
          <span>
            Page {page} of {totalPages} &middot; {total} orders
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="rounded-full border border-slate-200 px-4 py-2 font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              className="rounded-full border border-slate-200 px-4 py-2 font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {selectedOrderId && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/50 px-4 py-10">
          <div className="w-full max-w-3xl rounded-3xl bg-white p-7 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-xl font-bold text-slate-950">Order details</h3>
                <p className="mt-1 font-mono text-xs text-slate-500">{selectedOrderId}</p>
              </div>
              <button
                type="button"
                onClick={closeDetail}
                className="rounded-full px-3 py-1 text-sm font-semibold text-slate-500 hover:bg-slate-100"
              >
                Close
              </button>
            </div>

            {detailLoading ? (
              <div className="py-16 text-center text-slate-500">Loading order...</div>
            ) : detailError ? (
              <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700">
                {detailError}
              </div>
            ) : selectedOrder ? (
              <div className="mt-6 space-y-6">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Customer</p>
                    <p className="mt-1 font-semibold text-slate-900">
                      {selectedOrder.customer_name ?? "—"}
                    </p>
                    <p className="text-sm text-slate-600">{selectedOrder.customer_email}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Shipping address</p>
                    <p className="mt-1 whitespace-pre-line text-sm text-slate-700">
                      {selectedOrder.shipping_address || "Not provided"}
                    </p>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Order status</p>
                    <div className="mt-2">
                      <StatusPill status={selectedOrder.status} />
                    </div>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Payment</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {selectedOrder.payment_status} &middot; {selectedOrder.payment_method}
                    </p>

                    {selectedOrder.payment_method === "stripe" &&
                      selectedOrder.payment_status !== "paid" &&
                      selectedOrder.payment_status !== "refunded" && (
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={() => void handleConfirmPayment()}
                            disabled={confirmPaymentLoading}
                            className="rounded-full bg-slate-950 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-slate-800 disabled:opacity-50"
                          >
                            {confirmPaymentLoading ? "Checking with Stripe..." : "Confirm Payment"}
                          </button>
                          {confirmPaymentResult && (
                            <p
                              className={`mt-2 text-xs ${
                                confirmPaymentResult.type === "success"
                                  ? "text-emerald-700"
                                  : confirmPaymentResult.type === "error"
                                    ? "text-rose-700"
                                    : "text-slate-500"
                              }`}
                            >
                              {confirmPaymentResult.text}
                            </p>
                          )}
                        </div>
                      )}
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">Total</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {formatMoney(selectedOrder)}
                    </p>
                  </div>
                </div>

                <div className="rounded-2xl bg-slate-50 p-4 text-xs text-slate-500">
                  <div className="grid gap-1 sm:grid-cols-3">
                    <span>Created: {formatDateTime(selectedOrder.created_at)}</span>
                    <span>Updated: {formatDateTime(selectedOrder.updated_at)}</span>
                    <span>Delivered: {formatDateTime(selectedOrder.delivered_at)}</span>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-bold uppercase tracking-wide text-slate-500">Items</h4>
                  <div className="mt-2 space-y-2">
                    {selectedOrder.items.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3 text-sm"
                      >
                        <div>
                          <p className="font-semibold text-slate-900">{item.product_name ?? "Product"}</p>
                          <p className="text-xs text-slate-500">
                            Qty {item.quantity} &middot; {selectedOrder.currency.toUpperCase()}{" "}
                            {Number(item.unit_price).toFixed(2)} each
                          </p>
                        </div>
                        <p className="font-semibold text-slate-900">
                          {selectedOrder.currency.toUpperCase()}{" "}
                          {(Number(item.unit_price) * item.quantity).toFixed(2)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                    Move to next status
                  </h4>
                  {NEXT_STATUSES[selectedOrder.status]?.length ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {NEXT_STATUSES[selectedOrder.status].map((next) => (
                        <button
                          key={next}
                          type="button"
                          onClick={() => {
                            setStatusDialogError("");
                            setPendingStatus(next);
                          }}
                          className="rounded-full bg-slate-950 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-slate-800"
                        >
                          Mark as {next.replace(/_/g, " ")}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-500">
                      No further status changes available for this order.
                    </p>
                  )}
                </div>

                {selectedOrder.status_history && selectedOrder.status_history.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold uppercase tracking-wide text-slate-500">
                      Status history
                    </h4>
                    <ul className="mt-2 space-y-1.5 text-xs text-slate-600">
                      {selectedOrder.status_history.map((entry) => (
                        <li key={entry.id} className="flex flex-wrap items-center gap-1.5">
                          <span className="font-semibold text-slate-800">
                            {entry.previous_status
                              ? `${entry.previous_status} → ${entry.new_status}`
                              : `created as ${entry.new_status}`}
                          </span>
                          <span>
                            by {entry.changed_by_name ?? "system"} &middot;{" "}
                            {formatDateTime(entry.created_at)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedOrder.return_request && (
                  <div className="rounded-2xl border border-violet-200 bg-violet-50 p-5">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-bold uppercase tracking-wide text-violet-800">
                        Return request
                      </h4>
                      <StatusPill
                        status={selectedOrder.return_request.status}
                        styles={RETURN_STATUS_STYLES}
                      />
                    </div>

                    <dl className="mt-3 space-y-2 text-sm text-slate-700">
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-slate-500">Reason</dt>
                        <dd>{selectedOrder.return_request.reason}</dd>
                      </div>
                      {selectedOrder.return_request.comments && (
                        <div>
                          <dt className="text-xs uppercase tracking-wide text-slate-500">
                            Customer comments
                          </dt>
                          <dd>{selectedOrder.return_request.comments}</dd>
                        </div>
                      )}
                      <div className="text-xs text-slate-500">
                        Requested {formatDateTime(selectedOrder.return_request.created_at)}
                      </div>
                      {selectedOrder.return_request.reviewed_by_name && (
                        <div className="text-xs text-slate-500">
                          Reviewed by {selectedOrder.return_request.reviewed_by_name} on{" "}
                          {formatDateTime(selectedOrder.return_request.reviewed_at)}
                          {selectedOrder.return_request.review_comment && (
                            <> — &ldquo;{selectedOrder.return_request.review_comment}&rdquo;</>
                          )}
                        </div>
                      )}
                    </dl>

                    {selectedOrder.return_request.history &&
                      selectedOrder.return_request.history.length > 0 && (
                        <ul className="mt-3 space-y-1 border-t border-violet-200 pt-3 text-xs text-slate-600">
                          {selectedOrder.return_request.history.map((entry) => (
                            <li key={entry.id}>
                              {entry.previous_status
                                ? `${entry.previous_status} → ${entry.new_status}`
                                : `submitted as ${entry.new_status}`}{" "}
                              by {entry.changed_by_name ?? "customer"} &middot;{" "}
                              {formatDateTime(entry.created_at)}
                              {entry.comment && <> — &ldquo;{entry.comment}&rdquo;</>}
                            </li>
                          ))}
                        </ul>
                      )}

                    {selectedOrder.return_request.status === "pending" && (
                      <div className="mt-4 flex gap-3">
                        <button
                          type="button"
                          onClick={() => {
                            setReturnDialogError("");
                            setReturnDialog("approve");
                          }}
                          className="rounded-full bg-emerald-600 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-emerald-500"
                        >
                          Accept return
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setReturnDialogError("");
                            setReturnDialog("reject");
                          }}
                          className="rounded-full bg-rose-600 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-rose-500"
                        >
                          Reject return
                        </button>
                      </div>
                    )}

                    {(selectedOrder.return_request.status === "approved" ||
                      selectedOrder.return_request.status === "returned") && (
                      <div className="mt-4">
                        <button
                          type="button"
                          onClick={() => {
                            setReturnDialogError("");
                            setReturnDialog("refund");
                          }}
                          className="rounded-full bg-cyan-600 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-cyan-500"
                        >
                          Initiate refund
                        </button>
                        <p className="mt-2 text-xs text-slate-500">
                          {selectedOrder.return_request.status === "approved"
                            ? "This will mark the item as returned and refund the customer's payment."
                            : "This will refund the customer's payment for this order."}
                        </p>
                      </div>
                    )}

                    {selectedOrder.return_request.status === "refunded" && (
                      <p className="mt-4 text-sm font-medium text-cyan-700">
                        Refund processed — the customer has been reimbursed.
                      </p>
                    )}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {pendingStatus && selectedOrder && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/60 px-6">
          <div className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-950">Confirm status change</h3>
            <p className="mt-2 text-sm text-slate-600">
              Move order <span className="font-mono text-xs">{selectedOrder.id.slice(0, 8)}…</span>{" "}
              from <strong>{selectedOrder.status.replace(/_/g, " ")}</strong> to{" "}
              <strong>{pendingStatus.replace(/_/g, " ")}</strong>?
            </p>
            {statusDialogError && (
              <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {statusDialogError}
              </p>
            )}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={statusActionLoading}
                onClick={() => {
                  setStatusDialogError("");
                  setPendingStatus(null);
                }}
                className="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={statusActionLoading}
                onClick={() => void confirmStatusChange()}
                className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                {statusActionLoading ? "Updating..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {returnDialog && selectedOrder && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/60 px-6">
          <div className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-950">
              {returnDialog === "approve"
                ? "Accept return request"
                : returnDialog === "reject"
                  ? "Reject return request"
                  : "Initiate refund"}
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              {returnDialog === "approve"
                ? "Optionally add a note for the record."
                : returnDialog === "reject"
                  ? "A reason is required so the customer understands the decision."
                  : "This will call Stripe to refund the customer's payment for this order. Optionally add a note for the record."}
            </p>
            <textarea
              value={returnComment}
              onChange={(e) => setReturnComment(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder={returnDialog === "reject" ? "Reason for rejection" : "Optional comment"}
              className="mt-4 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500"
            />
            {returnDialogError && (
              <p className="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {returnDialogError}
              </p>
            )}
            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={returnActionLoading}
                onClick={() => {
                  setReturnDialog(null);
                  setReturnComment("");
                  setReturnDialogError("");
                }}
                className="rounded-full px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={returnActionLoading || (returnDialog === "reject" && !returnComment.trim())}
                onClick={() => void confirmReturnDecision()}
                className={`rounded-full px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${
                  returnDialog === "approve"
                    ? "bg-emerald-600 hover:bg-emerald-500"
                    : returnDialog === "reject"
                      ? "bg-rose-600 hover:bg-rose-500"
                      : "bg-cyan-600 hover:bg-cyan-500"
                }`}
              >
                {returnActionLoading
                  ? returnDialog === "refund"
                    ? "Processing refund..."
                    : "Saving..."
                  : returnDialog === "approve"
                    ? "Confirm accept"
                    : returnDialog === "reject"
                      ? "Confirm reject"
                      : "Confirm refund"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

// ---------------------------------------------------------------------------
// Route entry point: resolve the signed-in user's role once, then delegate
// to the matching view. Both views live at the same /orders URL.
// ---------------------------------------------------------------------------

type ViewRole = "resolving" | "admin" | "customer";

export default function OrdersPage() {
  const [viewRole, setViewRole] = useState<ViewRole>("resolving");

  useEffect(() => {
    const resolveRole = async () => {
      const signedIn = await isAuthenticated();
      if (!signedIn) {
        setViewRole("customer"); // CustomerOrdersView shows the login prompt
        return;
      }
      try {
        const user = await fetchCurrentUser();
        setViewRole(user.role === "admin" || user.role === "staff" ? "admin" : "customer");
      } catch {
        setViewRole("customer");
      }
    };
    void resolveRole();
  }, []);

  if (viewRole === "resolving") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_#fff7ed,_#f8fafc_45%,_#e0f2fe_100%)] text-slate-500">
        Loading...
      </main>
    );
  }

  return viewRole === "admin" ? <AdminOrdersView /> : <CustomerOrdersView />;
}
