import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildNotificationSocketUrl,
  fetchNotifications,
  notifyCartChanged,
  notifyOrderStatusChanged,
  onCartChanged,
  onOrderStatusChanged,
  OrderStatusUpdatedPayload,
} from "./storefront";

describe("cart-changed event bus", () => {
  it("delivers notifyCartChanged() to a listener registered via onCartChanged()", () => {
    const handler = vi.fn();
    const unsubscribe = onCartChanged(handler);

    notifyCartChanged();

    expect(handler).toHaveBeenCalledTimes(1);

    unsubscribe();
    notifyCartChanged();

    expect(handler).toHaveBeenCalledTimes(1);
  });
});

describe("order-status-changed event bus", () => {
  it("delivers the exact payload passed to notifyOrderStatusChanged()", () => {
    const handler = vi.fn<(payload: OrderStatusUpdatedPayload) => void>();
    const unsubscribe = onOrderStatusChanged(handler);

    const payload: OrderStatusUpdatedPayload = {
      order_id: "order-1",
      old_status: "paid",
      new_status: "shipped",
      payment_status: "paid",
      message: "Your order order-1 has been shipped.",
      timestamp: "2026-08-24T00:00:00Z",
    };

    notifyOrderStatusChanged(payload);

    expect(handler).toHaveBeenCalledWith(payload);

    unsubscribe();
  });

  it("only calls handlers still subscribed at dispatch time", () => {
    const first = vi.fn();
    const second = vi.fn();

    const unsubscribeFirst = onOrderStatusChanged(first);
    onOrderStatusChanged(second);

    unsubscribeFirst();

    notifyOrderStatusChanged({
      order_id: "order-2",
      old_status: "shipped",
      new_status: "delivered",
      message: "Delivered",
      timestamp: "2026-08-24T00:00:00Z",
    });

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
  });
});

describe("buildNotificationSocketUrl", () => {
  it("appends the token as a URL-encoded query param on the ws:// endpoint", () => {
    const url = buildNotificationSocketUrl("abc.def+ghi/jkl");

    expect(url).toMatch(/^ws:\/\/.*\/ws\/notifications\?token=/);
    expect(url).toContain(encodeURIComponent("abc.def+ghi/jkl"));
  });
});

function fakeJwt(expiresInSeconds: number) {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expiresInSeconds })
  );
  return `${header}.${payload}.signature`;
}

describe("fetchNotifications", () => {
  beforeEach(() => {
    window.localStorage.setItem(
      "smart_customer_access_token",
      fakeJwt(3600)
    );
  });

  afterEach(() => {
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("unwraps the paginated envelope into a plain array for existing callers", async () => {
    const items = [
      {
        id: "n1",
        user_id: "u1",
        type: "order_confirmed",
        message: "Your order has been confirmed.",
        read_status: false,
        timestamp: "2026-08-24T00:00:00Z",
      },
    ];

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items,
        page: 1,
        page_size: 100,
        total: 1,
        total_pages: 1,
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchNotifications();

    expect(result).toEqual(items);

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/notifications");
    expect(url).toContain("page=1");
    expect(url).toContain("page_size=100");
  });
});
