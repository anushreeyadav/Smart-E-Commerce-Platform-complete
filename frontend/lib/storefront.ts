export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface Product {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  price: number;
  stock: number;
  images?: string[];
  popularity: number;
}

export interface CartItem {
  id: string;
  user_id: string;
  product_id: string;
  quantity: number;
  unit_price: number;
  item_total: number;
  product: Product | null;
}

export interface CartTotals {
  cart_total: number;
  tax_rate: number;
  tax: number;
  grand_total: number;
  total_items: number;
}

export interface CartResponse {
  items: CartItem[];
  totals: CartTotals;
}

export interface CartMutationResponse {
  message: string;
  item: CartItem;
  totals: CartTotals;
}

export interface CartRemovalResponse {
  message: string;
  totals: CartTotals;
}

export interface CheckoutRequest {
  payment_method?: string;
  currency?: string;
  success_url?: string;
  cancel_url?: string;
}

export interface CheckoutResponse {
  message: string;
  order: {
    id: string;
    user_id: string;
    status: string;
    payment_status: string;
    total_amount: number;
    payment_method: string;
    currency: string;
    stripe_checkout_session_id?: string | null;
    stripe_payment_intent_id?: string | null;
    created_at: string;
    items: Array<{
      id: string;
      product_id: string;
      quantity: number;
      unit_price: number;
      product_name?: string | null;
    }>;
  };
  payment: {
    id: string;
    order_id: string;
    amount: number;
    payment_method: string;
    status: string;
    transaction_id?: string | null;
    paid_at?: string | null;
    timestamp: string;
    created_at: string;
  };
  checkout_session_id?: string | null;
  checkout_session_url?: string | null;
  payment_intent_id?: string | null;
  payment_intent_client_secret?: string | null;
}

export interface ProductFilters {
  category?: string;
  minPrice?: string;
  maxPrice?: string;
  popularity?: string;
  inStock?: string;
}

const CUSTOMER_ACCESS_TOKEN_KEY = "smart_customer_access_token";
const CUSTOMER_REFRESH_TOKEN_KEY = "smart_customer_refresh_token";
const AUTH_CHANGED_EVENT = "smart-auth-changed";
const CART_CHANGED_EVENT = "smart-cart-changed";
const ORDER_STATUS_CHANGED_EVENT = "smart-order-status-changed";

export function getCustomerAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(CUSTOMER_ACCESS_TOKEN_KEY);
}

function getCustomerRefreshToken() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(CUSTOMER_REFRESH_TOKEN_KEY);
}

function isTokenExpired(token: string) {
  try {
    const payload = token.split(".")[1];

    if (!payload) {
      return true;
    }

    const normalizedPayload = payload.replace(/-/g, "+").replace(/_/g, "/");
    const paddedPayload = normalizedPayload.padEnd(
      Math.ceil(normalizedPayload.length / 4) * 4,
      "="
    );
    const decodedPayload = JSON.parse(window.atob(paddedPayload)) as {
      exp?: number;
    };

    // Renew shortly before expiry so navigation does not race an expired token.
    return !decodedPayload.exp || decodedPayload.exp <= Date.now() / 1000 + 30;
  } catch {
    return true;
  }
}

export function saveCustomerTokens(
  accessToken: string,
  refreshToken?: string
) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(CUSTOMER_ACCESS_TOKEN_KEY, accessToken);

  if (refreshToken) {
    window.localStorage.setItem(CUSTOMER_REFRESH_TOKEN_KEY, refreshToken);
  }

  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function clearCustomerTokens() {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(CUSTOMER_ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(CUSTOMER_REFRESH_TOKEN_KEY);
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

async function refreshCustomerAccessToken() {
  const refreshToken = getCustomerRefreshToken();

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearCustomerTokens();
      return null;
    }

    const payload = (await response.json()) as {
      access_token?: string;
      refresh_token?: string;
    };

    if (!payload.access_token) {
      clearCustomerTokens();
      return null;
    }

    saveCustomerTokens(payload.access_token, payload.refresh_token);
    return payload.access_token;
  } catch {
    return null;
  }
}

export function onAuthChanged(handler: () => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const wrappedHandler = () => handler();
  window.addEventListener(AUTH_CHANGED_EVENT, wrappedHandler);
  window.addEventListener("storage", wrappedHandler);

  return () => {
    window.removeEventListener(AUTH_CHANGED_EVENT, wrappedHandler);
    window.removeEventListener("storage", wrappedHandler);
  };
}

export function notifyCartChanged() {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(new Event(CART_CHANGED_EVENT));
}

export function onCartChanged(handler: () => void) {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const wrappedHandler = () => handler();
  window.addEventListener(CART_CHANGED_EVENT, wrappedHandler);

  return () => {
    window.removeEventListener(CART_CHANGED_EVENT, wrappedHandler);
  };
}

export interface OrderStatusUpdatedPayload {
  order_id: string;
  old_status: string;
  new_status: string;
  payment_status?: string;
  message: string;
  timestamp: string;
}

export function notifyOrderStatusChanged(payload: OrderStatusUpdatedPayload) {
  if (typeof window === "undefined") {
    return;
  }

  window.dispatchEvent(
    new CustomEvent<OrderStatusUpdatedPayload>(ORDER_STATUS_CHANGED_EVENT, {
      detail: payload,
    })
  );
}

export function onOrderStatusChanged(
  handler: (payload: OrderStatusUpdatedPayload) => void
) {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const wrappedHandler = (event: Event) => {
    handler((event as CustomEvent<OrderStatusUpdatedPayload>).detail);
  };

  window.addEventListener(ORDER_STATUS_CHANGED_EVENT, wrappedHandler);

  return () => {
    window.removeEventListener(ORDER_STATUS_CHANGED_EVENT, wrappedHandler);
  };
}

function buildQuery(params: Record<string, string | undefined>) {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      searchParams.set(key, value);
    }
  }

  const query = searchParams.toString();
  return query ? `?${query}` : "";
}

export async function fetchProducts(filters: ProductFilters = {}) {
  const query = buildQuery({
    category: filters.category,
    min_price: filters.minPrice,
    max_price: filters.maxPrice,
    popularity: filters.popularity,
    in_stock: filters.inStock,
  });

  const response = await fetch(`${API_BASE_URL}/products${query}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to fetch products");
  }

  return (await response.json()) as Product[];
}

export async function getBackendToken(forceRefresh = false) {
  const customerToken = getCustomerAccessToken();

  if (customerToken && !forceRefresh && !isTokenExpired(customerToken)) {
    return customerToken;
  }

  if (customerToken || getCustomerRefreshToken()) {
    return refreshCustomerAccessToken();
  }

  const response = await fetch("/api/backend-token", {
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response
      .json()
      .catch(() => ({ detail: "Unable to create a backend session" }));
    throw new Error(
      payload.detail ?? "Unable to create a backend session"
    );
  }

  const data = (await response.json()) as {
    backendAccessToken?: string;
  };

  return data.backendAccessToken ?? null;
}

export async function isAuthenticated() {
  if (getCustomerAccessToken() || getCustomerRefreshToken()) {
    return Boolean(await getBackendToken());
  }

  const response = await fetch("/api/me", {
    cache: "no-store",
  });

  return response.ok;
}

async function authedFetch<T>(
  path: string,
  options: RequestInit = {},
  retryAfterRefresh = true
): Promise<T> {
  const backendAccessToken = await getBackendToken();

  if (!backendAccessToken) {
    throw new Error("Please log in to access your cart.");
  }

  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${backendAccessToken}`);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && retryAfterRefresh) {
    const refreshedToken = await getBackendToken(true);

    if (refreshedToken) {
      return authedFetch(path, options, false);
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearCustomerTokens();
    }

    const payload = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail ?? "Request failed");
  }

  return (await response.json()) as T;
}

export async function fetchCart() {
  return authedFetch<CartResponse>("/cart");
}

export async function fetchCartCount() {
  const cart = await fetchCart();
  return cart.totals.total_items;
}

export async function addToCart(productId: string, quantity: number) {
  const response = await authedFetch<CartMutationResponse>("/cart/add", {
    method: "POST",
    body: JSON.stringify({
      product_id: productId,
      quantity,
    }),
  });

  notifyCartChanged();
  return response;
}

export async function updateCartItem(productId: string, quantity: number) {
  const response = await authedFetch<CartMutationResponse>("/cart/update", {
    method: "PUT",
    body: JSON.stringify({
      product_id: productId,
      quantity,
    }),
  });

  notifyCartChanged();
  return response;
}

export async function removeFromCart(productId: string) {
  const response = await authedFetch<CartRemovalResponse>("/cart/remove", {
    method: "DELETE",
    body: JSON.stringify({
      product_id: productId,
    }),
  });

  notifyCartChanged();
  return response;
}

export async function createCheckoutSession(
  request: CheckoutRequest = {}
) {
  return authedFetch<CheckoutResponse>("/checkout", {
    method: "POST",
    body: JSON.stringify({
      payment_method: request.payment_method ?? "stripe",
      currency: request.currency ?? "usd",
      success_url: request.success_url,
      cancel_url: request.cancel_url,
    }),
  });
}
export interface Notification {
  id: string;
  user_id: string;
  type: string;
  message: string;
  read_status: boolean;
  timestamp: string;
}

export interface NotificationListResponse {
  items: Notification[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface MarkNotificationsReadResponse {
  message: string;
  updated_count: number;
}

export async function fetchNotificationsPage(
  params: { page?: number; pageSize?: number; read?: boolean } = {}
) {
  const query = buildQuery({
    page: params.page ? String(params.page) : undefined,
    page_size: params.pageSize ? String(params.pageSize) : undefined,
    read: params.read === undefined ? undefined : String(params.read),
  });

  return authedFetch<NotificationListResponse>(`/notifications${query}`);
}

export async function fetchNotifications() {
  const response = await fetchNotificationsPage({ page: 1, pageSize: 100 });
  return response.items;
}

export async function markNotificationsAsRead(
  notificationIds: string[] = [],
  markAll = false
) {
  return authedFetch<MarkNotificationsReadResponse>(
    "/notifications/read",
    {
      method: "POST",
      body: JSON.stringify({
        notification_ids: notificationIds,
        mark_all: markAll,
      }),
    }
  );
}

export interface OrderItem {
  id: string;
  product_id: string;
  quantity: number;
  unit_price: number;
  product_name?: string | null;
}

export interface Order {
  id: string;
  user_id: string;
  status: string;
  payment_status: string;
  total_amount: number;
  payment_method: string;
  currency: string;
  stripe_checkout_session_id?: string | null;
  stripe_payment_intent_id?: string | null;
  created_at: string;
  items: OrderItem[];
}

export async function fetchMyOrders() {
  return authedFetch<Order[]>("/orders/me");
}

export async function fetchOrder(orderId: string) {
  return authedFetch<Order>(`/orders/${orderId}`);
}

export function getWebSocketUrl() {
  return API_BASE_URL.replace(/^http/, "ws");
}

export function buildNotificationSocketUrl(token: string) {
  return `${getWebSocketUrl()}/ws/notifications?token=${encodeURIComponent(
    token
  )}`;
}
