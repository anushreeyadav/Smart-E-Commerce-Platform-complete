"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { fetchCartCount, onAuthChanged, onCartChanged } from "@/lib/storefront";
import { useAuth } from "@/components/auth-provider";

type CartContextValue = {
  itemCount: number;
  refreshCartCount: () => Promise<void>;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { isLoggedIn } = useAuth();
  const [itemCount, setItemCount] = useState(0);

  const refreshCartCount = async () => {
    if (!isLoggedIn) {
      setItemCount(0);
      return;
    }

    try {
      const count = await fetchCartCount();
      setItemCount(count);
    } catch {
      setItemCount(0);
    }
  };

  useEffect(() => {
    void refreshCartCount();

    const unsubscribeAuth = onAuthChanged(() => {
      void refreshCartCount();
    });

    const unsubscribeCart = onCartChanged(() => {
      void refreshCartCount();
    });

    return () => {
      unsubscribeAuth();
      unsubscribeCart();
    };
  }, [isLoggedIn]);

  const value = useMemo<CartContextValue>(
    () => ({
      itemCount,
      refreshCartCount,
    }),
    [itemCount]
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);

  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }

  return context;
}
