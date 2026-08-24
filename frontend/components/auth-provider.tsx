"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  clearCustomerTokens,
  getCustomerAccessToken,
  onAuthChanged,
} from "@/lib/storefront";

type AuthContextValue = {
  isLoggedIn: boolean;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const syncAuthState = () => {
      setIsLoggedIn(Boolean(getCustomerAccessToken()));
    };

    syncAuthState();
    return onAuthChanged(syncAuthState);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isLoggedIn,
      logout: () => {
        clearCustomerTokens();
        setIsLoggedIn(false);
      },
    }),
    [isLoggedIn]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }

  return context;
}
