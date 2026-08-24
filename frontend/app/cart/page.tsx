"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import CartNavLink from "@/components/cart-nav-link";
import NotificationBell from "@/components/notification-bell";
import {
  createCheckoutSession,
  CartResponse,
  fetchCart,
  isAuthenticated,
  removeFromCart,
  updateCartItem,
} from "@/lib/storefront";

function CartPageContent() {
  const [cart, setCart] = useState<CartResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyProductId, setBusyProductId] = useState("");
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const searchParams = useSearchParams();

  const loadCart = async () => {
    setLoading(true);
    setError("");

    try {
      const signedIn = await isAuthenticated();

      if (!signedIn) {
        setAuthenticated(false);
        setCart(null);
        return;
      }

      setAuthenticated(true);

      const data = await fetchCart();
      setCart(data);

      const nextQuantities: Record<string, string> = {};
      data.items.forEach((item) => {
        nextQuantities[item.product_id] = String(item.quantity);
      });
      setQuantities(nextQuantities);
    } catch (fetchError) {
      const errorMessage =
        fetchError instanceof Error
          ? fetchError.message
          : "Unable to load cart.";
      setError(errorMessage);
      setCart(null);

      if (errorMessage === "Please log in to access your cart.") {
        setAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadCart();
  }, []);

  useEffect(() => {
    const checkoutState = searchParams.get("checkout");

    if (checkoutState === "success") {
      setMessage(
        "Payment completed successfully. Your order is now being processed."
      );
    } else if (checkoutState === "cancelled") {
      setMessage(
        "Checkout was cancelled. Your cart is still saved and ready when you are."
      );
    }
  }, [searchParams]);

  const handleQuantityChange = (
    productId: string,
    value: string
  ) => {
    setQuantities((current) => ({
      ...current,
      [productId]: value,
    }));
  };

  const handleQuantityUpdate = async (productId: string) => {
    const quantityValue = Number(quantities[productId]);

    if (!Number.isFinite(quantityValue) || quantityValue < 1) {
      setError("Quantity must be at least 1.");
      return;
    }

    setBusyProductId(productId);
    setError("");
    setMessage("");

    try {
      const response = await updateCartItem(
        productId,
        quantityValue
      );

      setCart((current) =>
        current
          ? {
              ...current,
              items: current.items.map((item) =>
                item.product_id === productId
                  ? response.item
                  : item
              ),
              totals: response.totals,
            }
          : current
      );

      setMessage(response.message);
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "Unable to update cart item."
      );
    } finally {
      setBusyProductId("");
    }
  };

  const handleRemove = async (productId: string) => {
    setBusyProductId(productId);
    setError("");
    setMessage("");

    try {
      const response = await removeFromCart(productId);

      setCart((current) =>
        current
          ? {
              ...current,
              items: current.items.filter(
                (item) => item.product_id !== productId
              ),
              totals: response.totals,
            }
          : current
      );

      setQuantities((current) => {
        const next = { ...current };
        delete next[productId];
        return next;
      });

      setMessage(response.message);
    } catch (removeError) {
      setError(
        removeError instanceof Error
          ? removeError.message
          : "Unable to remove cart item."
      );
    } finally {
      setBusyProductId("");
    }
  };

  const handleCheckout = async () => {
    setCheckoutLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await createCheckoutSession();
      const checkoutUrl = response.checkout_session_url;

      if (!checkoutUrl) {
        throw new Error(
          "Stripe checkout URL was not returned."
        );
      }

      window.location.assign(checkoutUrl);
    } catch (checkoutError) {
      setError(
        checkoutError instanceof Error
          ? checkoutError.message
          : "Unable to start checkout."
      );
      setCheckoutLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#f8fafc_45%,_#e0f2fe_100%)] text-slate-900">
      <header className="border-b border-white/70 bg-white/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">
              Smart E-Commerce
            </h1>
            <p className="text-sm text-slate-500">
              Review and manage your cart
            </p>
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

            <Link
              href="/orders"
              className="text-sm font-medium text-slate-700 transition hover:text-slate-950"
            >
              Orders
            </Link>

            <CartNavLink />
            <NotificationBell />
            <AuthActionButton />
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-6 py-14">
        <div className="mb-8 rounded-3xl border border-white/70 bg-white/80 p-8 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-700">
            Cart System
          </p>

          <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-950">
            Edit quantities, remove products, and keep totals in sync.
          </h2>

          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            This page uses the FastAPI cart endpoints directly. If you are not
            logged in through Auth0, the page will prompt you to sign in.
          </p>
        </div>

        {message && (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-emerald-800">
            {message}
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-200 bg-rose-50 px-5 py-4 text-rose-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-3xl border border-white/70 bg-white/75 p-12 text-center text-slate-500 shadow-sm">
            Loading cart...
          </div>
        ) : authenticated === false ? (
          <div className="grid gap-6 lg:grid-cols-[1.5fr_0.9fr]">
            <div className="rounded-3xl border border-white/70 bg-white/80 p-10 shadow-sm">
              <h3 className="text-2xl font-bold text-slate-950">
                Please log in to view your cart
              </h3>

              <p className="mt-3 max-w-xl text-slate-600">
                The cart needs your Auth0 session so it can exchange it for a
                FastAPI access token.
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

            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-8 text-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
                Totals
              </p>

              <div className="mt-6 space-y-4 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Cart total</span>
                  <span>Rs. 0.00</span>
                </div>

                <div className="flex items-center justify-between">
                  <span>Tax</span>
                  <span>Rs. 0.00</span>
                </div>

                <div className="flex items-center justify-between border-t border-white/10 pt-4 text-base font-semibold text-white">
                  <span>Grand total</span>
                  <span>Rs. 0.00</span>
                </div>
              </div>
            </div>
          </div>
        ) : !cart || cart.items.length === 0 ? (
          <div className="grid gap-6 lg:grid-cols-[1.5fr_0.9fr]">
            <div className="rounded-3xl border border-white/70 bg-white/80 p-10 shadow-sm">
              <h3 className="text-2xl font-bold text-slate-950">
                Your cart is empty
              </h3>

              <p className="mt-3 max-w-xl text-slate-600">
                Browse the product catalog and add something to see your totals
                here.
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

            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-8 text-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
                Totals
              </p>

              <div className="mt-6 space-y-4 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Cart total</span>
                  <span>Rs. 0.00</span>
                </div>

                <div className="flex items-center justify-between">
                  <span>Tax</span>
                  <span>Rs. 0.00</span>
                </div>

                <div className="flex items-center justify-between border-t border-white/10 pt-4 text-base font-semibold text-white">
                  <span>Grand total</span>
                  <span>Rs. 0.00</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1.5fr_0.9fr]">
            <div className="space-y-4">
              {cart.items.map((item) => (
                <article
                  key={item.id}
                  className="rounded-3xl border border-white/70 bg-white/85 p-5 shadow-[0_20px_60px_rgba(15,23,42,0.08)]"
                >
                  <div className="grid gap-4 md:grid-cols-[120px_1fr]">
                    <div className="overflow-hidden rounded-2xl bg-slate-100">
                      {item.product?.images?.[0] ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={item.product.images[0]}
                          alt={item.product.name}
                          className="h-32 w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-32 items-center justify-center text-xs text-slate-400">
                          No image
                        </div>
                      )}
                    </div>

                    <div className="space-y-4">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h3 className="text-xl font-bold text-slate-950">
                            {item.product?.name ?? "Product"}
                          </h3>

                          <p className="mt-1 text-sm text-slate-500">
                            {item.product?.category ?? "general"}
                          </p>
                        </div>

                        <div className="text-left sm:text-right">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                            Item total
                          </p>

                          <p className="text-xl font-black text-slate-950">
                            Rs. {Number(item.item_total).toFixed(2)}
                          </p>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-3">
                        <div>
                          <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                            Quantity
                          </label>

                          <input
                            type="number"
                            min="1"
                            step="1"
                            value={
                              quantities[item.product_id] ?? item.quantity
                            }
                            onChange={(event) =>
                              handleQuantityChange(
                                item.product_id,
                                event.target.value
                              )
                            }
                            className="w-28 rounded-xl border border-slate-200 bg-white px-4 py-2 text-slate-900 outline-none transition focus:border-cyan-500"
                          />
                        </div>

                        <button
                          type="button"
                          disabled={busyProductId === item.product_id}
                          onClick={() =>
                            handleQuantityUpdate(item.product_id)
                          }
                          className="mt-6 rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                        >
                          {busyProductId === item.product_id
                            ? "Updating..."
                            : "Update"}
                        </button>

                        <button
                          type="button"
                          disabled={busyProductId === item.product_id}
                          onClick={() => handleRemove(item.product_id)}
                          className="mt-6 rounded-full border border-rose-300 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Remove
                        </button>
                      </div>

                      <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-3">
                        <div className="rounded-2xl bg-slate-50 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                            Unit price
                          </p>

                          <p className="mt-1 font-semibold text-slate-900">
                            Rs. {Number(item.unit_price).toFixed(2)}
                          </p>
                        </div>

                        <div className="rounded-2xl bg-slate-50 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                            Quantity
                          </p>

                          <p className="mt-1 font-semibold text-slate-900">
                            {item.quantity}
                          </p>
                        </div>

                        <div className="rounded-2xl bg-slate-50 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                            Stock
                          </p>

                          <p className="mt-1 font-semibold text-slate-900">
                            {item.product?.stock ?? "N/A"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <aside className="h-fit rounded-3xl border border-slate-200 bg-slate-950 p-8 text-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
                Order Summary
              </p>

              <div className="mt-6 space-y-4 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Items</span>
                  <span>{cart.totals.total_items}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span>Cart total</span>
                  <span>
                    Rs. {Number(cart.totals.cart_total).toFixed(2)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span>Tax</span>
                  <span>Rs. {Number(cart.totals.tax).toFixed(2)}</span>
                </div>

                <div className="flex items-center justify-between border-t border-white/10 pt-4 text-base font-semibold text-white">
                  <span>Grand total</span>
                  <span>
                    Rs. {Number(cart.totals.grand_total).toFixed(2)}
                  </span>
                </div>
              </div>

              <div className="mt-8 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                Need more products? Jump back to the catalog and keep shopping.
              </div>

              <button
                type="button"
                onClick={handleCheckout}
                disabled={checkoutLoading}
                className="mt-6 inline-flex w-full items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-cyan-200"
              >
                {checkoutLoading
                  ? "Redirecting to Stripe..."
                  : "Proceed to Checkout"}
              </button>

              <Link
                href="/products"
                prefetch={false}
                className="mt-4 inline-flex rounded-full bg-white/10 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/20"
              >
                Continue Shopping
              </Link>
            </aside>
          </div>
        )}
      </section>
    </main>
  );
}

export default function CartPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-600">
          Loading cart...
        </main>
      }
    >
      <CartPageContent />
    </Suspense>
  );
}
