"use client";

import Link from "next/link";
import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";

import AuthActionButton from "@/components/auth-action-button";
import CartNavLink from "@/components/cart-nav-link";
import NotificationBell from "@/components/notification-bell";
import {
  addToCart,
  isAuthenticated,
  fetchProducts,
  Product,
  ProductFilters,
} from "@/lib/storefront";

const initialFilters: ProductFilters = {
  category: "",
  minPrice: "",
  maxPrice: "",
  popularity: "",
  inStock: "",
};

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filters, setFilters] = useState<ProductFilters>(initialFilters);
  const [appliedFilters, setAppliedFilters] =
    useState<ProductFilters>(initialFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busyProductId, setBusyProductId] = useState("");

  useEffect(() => {
    const loadProducts = async () => {
      setLoading(true);
      setError("");

      try {
        const data = await fetchProducts(appliedFilters);
        setProducts(data);
      } catch (fetchError) {
        console.error(fetchError);
        setError("Unable to load products from the FastAPI backend.");
      } finally {
        setLoading(false);
      }
    };

    loadProducts();
  }, [appliedFilters]);

  const handleFilterChange = (
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  };

  const handleFilterSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage("");
    setAppliedFilters(filters);
  };

  const handleClearFilters = () => {
    setFilters(initialFilters);
    setAppliedFilters(initialFilters);
    setMessage("");
  };

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
      const errorMessage =
        cartError instanceof Error
          ? cartError.message
          : "Unable to add the item to cart.";
      setError(errorMessage);
    } finally {
      setBusyProductId("");
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#f7f1e8,_#f9fafb_45%,_#eef2ff_100%)] text-slate-900">
      <header className="border-b border-white/60 bg-white/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-950">
              Smart E-Commerce
            </h1>
            <p className="text-sm text-slate-500">Browse and filter the catalog</p>
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
              className="text-sm font-medium text-slate-950"
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
        <div className="mb-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-white/70 bg-white/80 p-8 shadow-[0_30px_80px_rgba(15,23,42,0.08)] backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-700">
              Product Catalog
            </p>
            <h2 className="mt-3 max-w-2xl text-4xl font-black tracking-tight text-slate-950">
              Explore products, narrow by filters, and add items to your cart.
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              The product list is driven directly from FastAPI and the cart uses
              your authenticated Auth0 session behind the scenes.
            </p>
          </div>

          <form
            onSubmit={handleFilterSubmit}
            className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-[0_24px_60px_rgba(15,23,42,0.18)]"
          >
            <div className="grid gap-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-200">
                  Category
                </label>
                <input
                  name="category"
                  value={filters.category}
                  onChange={handleFilterChange}
                  placeholder="electronics, fashion..."
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-400 focus:border-amber-400"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">
                    Min Price
                  </label>
                  <input
                    name="minPrice"
                    value={filters.minPrice}
                    onChange={handleFilterChange}
                    type="number"
                    min="0"
                    step="0.01"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-400 focus:border-amber-400"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">
                    Max Price
                  </label>
                  <input
                    name="maxPrice"
                    value={filters.maxPrice}
                    onChange={handleFilterChange}
                    type="number"
                    min="0"
                    step="0.01"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-400 focus:border-amber-400"
                  />
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">
                    Minimum Popularity
                  </label>
                  <input
                    name="popularity"
                    value={filters.popularity}
                    onChange={handleFilterChange}
                    type="number"
                    min="0"
                    step="1"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition placeholder:text-slate-400 focus:border-amber-400"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-200">
                    Stock
                  </label>
                  <select
                    name="inStock"
                    value={filters.inStock}
                    onChange={handleFilterChange}
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none transition focus:border-amber-400"
                  >
                    <option value="" className="text-slate-950">
                      Any
                    </option>
                    <option value="true" className="text-slate-950">
                      In stock only
                    </option>
                    <option value="false" className="text-slate-950">
                      Out of stock only
                    </option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  className="rounded-full bg-amber-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-300"
                >
                  Apply Filters
                </button>
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="rounded-full border border-white/15 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  Reset
                </button>
              </div>
            </div>
          </form>
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
            Loading products...
          </div>
        ) : products.length === 0 ? (
          <div className="rounded-3xl border border-white/70 bg-white/75 p-12 text-center text-slate-500 shadow-sm">
            No products match the selected filters.
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {products.map((product) => (
              <article
                key={product.id}
                className="overflow-hidden rounded-3xl border border-white/70 bg-white/90 shadow-[0_20px_60px_rgba(15,23,42,0.08)] transition hover:-translate-y-1 hover:shadow-[0_24px_70px_rgba(15,23,42,0.12)]"
              >
                <div className="relative h-56 bg-slate-100">
                  {product.images?.[0] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={product.images[0]}
                      alt={product.name}
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-slate-400">
                      No image available
                    </div>
                  )}
                  <div className="absolute left-4 top-4 rounded-full bg-slate-950/85 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-white">
                    {product.category}
                  </div>
                </div>

                <div className="space-y-4 p-5">
                  <div>
                    <h3 className="text-xl font-bold text-slate-950">
                      {product.name}
                    </h3>
                    <p className="mt-2 line-clamp-3 text-sm leading-6 text-slate-600">
                      {product.description || "No description available."}
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                        Price
                      </p>
                      <p className="text-2xl font-black text-slate-950">
                        Rs. {Number(product.price).toFixed(2)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-400">
                        Popularity
                      </p>
                      <p className="text-lg font-semibold text-slate-700">
                        {product.popularity}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span
                      className={`text-sm font-semibold ${
                        product.stock > 0 ? "text-emerald-700" : "text-rose-600"
                      }`}
                    >
                      {product.stock > 0
                        ? `${product.stock} in stock`
                        : "Out of stock"}
                    </span>

                    <button
                      type="button"
                      disabled={product.stock <= 0 || busyProductId === product.id}
                      onClick={() => handleAddToCart(product.id)}
                      className="rounded-full bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
                    >
                      {busyProductId === product.id
                        ? "Adding..."
                        : product.stock > 0
                          ? "Add to Cart"
                          : "Out of Stock"}
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
