import type { Metadata } from "next";

import { AuthProvider } from "@/components/auth-provider";
import { CartProvider } from "@/components/cart-provider";
import { NotificationProvider } from "@/components/notification-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "Smart E-Commerce",
  description: "Smart E-Commerce storefront with product catalog and cart.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <AuthProvider>
          <NotificationProvider>
            <CartProvider>{children}</CartProvider>
          </NotificationProvider>
        </AuthProvider>
      </body>
    </html>
  );
}