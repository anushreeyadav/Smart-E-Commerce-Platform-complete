"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import CartNavLink from "@/components/cart-nav-link";
import NotificationBell from "@/components/notification-bell";
import {
  addToCart,
  fetchProducts,
  isAuthenticated,
  Product,
} from "@/lib/storefront";

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyProductId, setBusyProductId] = useState("");

  useEffect(() => {
    const loadProducts = async () => {
      try {
        const data = await fetchProducts();
        setProducts(data.slice(0, 6));
      } catch (fetchError) {
        console.error(fetchError);
        setError("Unable to connect to the backend. Make sure FastAPI is running.");
      } finally {
        setLoading(false);
      }
    };

    loadProducts();
  }, []);

  const handleAddToCart = async (productId: string) => {
    setBusyProductId(productId);
    setMessage("");
    setError("");

    try {
      const signedIn = await isAuthenticated();

      if (!signedIn) {
        setError("Please log in first to add items to your cart.");
        window.location.href = "/customer-login";
        return;
      }

      const response = await addToCart(productId, 1);
      setMessage(
        `${response.item.product?.name ?? "Product"} added to cart successfully.`
      );
    } catch (cartError) {
      setError(
        cartError instanceof Error
          ? cartError.message
          : "Unable to add the item to cart."
      );
    } finally {
      setBusyProductId("");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <header className="border-b border-white/10 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Smart E-Commerce</h1>
            <p className="text-sm text-slate-400">Shop smart. Shop better.</p>
          </div>

          <nav className="flex items-center gap-6">
            <Link href="/" className="text-sm font-medium text-white">
              Home
            </Link>
            <Link
              href="/products"
              className="text-sm font-medium text-slate-300 transition hover:text-white"
            >
              Products
            </Link>
            <Link
              href="/orders"
              className="text-sm font-medium text-slate-300 transition hover:text-white"
            >
              Orders
            </Link>
            <CartNavLink />
            <NotificationBell />
            <AuthActionButton />
          </nav>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-white/10 bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.28),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.22),_transparent_24%),linear-gradient(135deg,_#020617,_#0f172a_60%,_#111827)]">
        <div className="mx-auto grid max-w-7xl gap-12 px-6 py-24 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
          <div>
            <p className="inline-flex rounded-full border border-amber-300/30 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-amber-200">
              Smart Commerce Platform
            </p>
            <h2 className="mt-6 max-w-3xl text-5xl font-black leading-tight tracking-tight sm:text-6xl">
              Discover products, filter faster, and shop with confidence.
            </h2>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              Browse the latest catalog from FastAPI, add items directly to your
              authenticated cart, and keep your shopping flow moving without
              jumping between tools.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/products"
                className="rounded-full bg-amber-400 px-6 py-3 font-semibold text-slate-950 transition hover:bg-amber-300"
              >
                Browse Products
              </Link>
              <Link
                href="/cart"
                className="rounded-full border border-white/15 px-6 py-3 font-semibold text-white transition hover:bg-white/10"
              >
                Open Cart
              </Link>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-white/8 p-4">
                <p className="text-sm text-slate-400">FastAPI</p>
                <p className="mt-2 text-2xl font-black">Catalog + Cart</p>
              </div>
              <div className="rounded-2xl bg-white/8 p-4">
                <p className="text-sm text-slate-400">Auth0</p>
                <p className="mt-2 text-2xl font-black">Social Login</p>
              </div>
              <div className="rounded-2xl bg-white/8 p-4">
                <p className="text-sm text-slate-400">Filtering</p>
                <p className="mt-2 text-2xl font-black">Category + Price</p>
              </div>
              <div className="rounded-2xl bg-white/8 p-4">
                <p className="text-sm text-slate-400">Totals</p>
                <p className="mt-2 text-2xl font-black">Tax + Grand Total</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-16">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-3xl font-black tracking-tight text-white">
              Featured Products
            </h2>
            <p className="mt-2 text-slate-400">
              Live products from the backend catalog.
            </p>
          </div>

          <Link
            href="/products"
            className="text-sm font-semibold text-amber-300 transition hover:text-amber-200"
          >
            View all products
          </Link>
        </div>

        {message && (
          <div className="mb-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-5 py-4 text-emerald-200">
            {message}
          </div>
        )}

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-400/20 bg-rose-400/10 px-5 py-4 text-rose-200">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-12 text-center text-slate-400">
            Loading products...
          </div>
        ) : products.length === 0 ? (
          <div className="rounded-3xl border border-white/10 bg-white/5 p-12 text-center text-slate-400">
            No products available.
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {products.map((product) => (
              <article
                key={product.id}
                className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 shadow-[0_20px_60px_rgba(15,23,42,0.35)] transition hover:-translate-y-1 hover:bg-white/8"
              >
                <div className="relative h-56 bg-slate-900">
                  {product.images?.[0] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={product.images[0]}
                      alt={product.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-slate-500">
                      No image available
                    </div>
                  )}
                  <div className="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-950">
                    {product.category}
                  </div>
                </div>

                <div className="space-y-4 p-5">
                  <div>
                    <h3 className="text-xl font-bold text-white">
                      {product.name}
                    </h3>
                    <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-300">
                      {product.description || "No description available."}
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                        Price
                      </p>
                      <p className="text-2xl font-black text-white">
                        Rs. {Number(product.price).toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                        Stock
                      </p>
                      <p className="text-lg font-semibold text-slate-200">
                        {product.stock > 0
                          ? `${product.stock} available`
                          : "Out of stock"}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    disabled={product.stock <= 0 || busyProductId === product.id}
                    onClick={() => handleAddToCart(product.id)}
                    className="w-full rounded-full bg-amber-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:bg-slate-600"
                  >
                    {busyProductId === product.id
                      ? "Adding..."
                      : product.stock > 0
                        ? "Add to Cart"
                        : "Out of Stock"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <footer className="border-t border-white/10 bg-slate-950">
        <div className="mx-auto max-w-7xl px-6 py-8 text-center text-sm text-slate-500">
          Copyright 2026 Smart E-Commerce. All rights reserved.
        </div>
      </footer>
    </main>
  );
}
