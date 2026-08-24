import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const useAuthMock = vi.fn();

vi.mock("@/components/auth-provider", () => ({
  useAuth: () => useAuthMock(),
}));

const fetchNotificationsMock = vi.fn();
const getBackendTokenMock = vi.fn();
const markNotificationsAsReadMock = vi.fn();
const notifyCartChangedMock = vi.fn();
const notifyOrderStatusChangedMock = vi.fn();

vi.mock("@/lib/storefront", async () => {
  const actual = await vi.importActual<typeof import("@/lib/storefront")>(
    "@/lib/storefront"
  );

  return {
    ...actual,
    fetchNotifications: (...args: unknown[]) => fetchNotificationsMock(...args),
    getBackendToken: (...args: unknown[]) => getBackendTokenMock(...args),
    markNotificationsAsRead: (...args: unknown[]) =>
      markNotificationsAsReadMock(...args),
    notifyCartChanged: (...args: unknown[]) => notifyCartChangedMock(...args),
    notifyOrderStatusChanged: (...args: unknown[]) =>
      notifyOrderStatusChangedMock(...args),
    buildNotificationSocketUrl: (token: string) =>
      `ws://test.local/ws/notifications?token=${token}`,
  };
});

const { NotificationProvider, useNotifications } = await import(
  "./notification-provider"
);

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    if (this.readyState === MockWebSocket.CLOSED) return;
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  emitOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  emitMessage(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  emitClose() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }
}

function Probe() {
  const { notifications, unreadCount } = useNotifications();
  return (
    <div>
      <div data-testid="unread-count">{unreadCount}</div>
      <div data-testid="notification-count">{notifications.length}</div>
      <ul>
        {notifications.map((n) => (
          <li key={n.id}>{n.message}</li>
        ))}
      </ul>
    </div>
  );
}

describe("NotificationProvider WebSocket lifecycle", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    fetchNotificationsMock.mockResolvedValue([]);
    getBackendTokenMock.mockResolvedValue("test-token");
    useAuthMock.mockReturnValue({ isLoggedIn: true, logout: vi.fn() });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("opens exactly one socket with the token in the URL when logged in", async () => {
    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    expect(MockWebSocket.instances[0].url).toContain("token=test-token");
  });

  it("does not connect at all when logged out", async () => {
    useAuthMock.mockReturnValue({ isLoggedIn: false, logout: vi.fn() });

    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await waitFor(() => expect(fetchNotificationsMock).not.toHaveBeenCalled());
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it("prepends a notification_created event and updates the unread count", async () => {
    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    const socket = MockWebSocket.instances[0];

    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        event: "notification_created",
        data: {
          id: "n1",
          user_id: "u1",
          type: "order_confirmed",
          message: "Your order has been confirmed.",
          read_status: false,
          timestamp: "2026-08-24T10:00:00Z",
        },
      });
    });

    expect(screen.getByTestId("unread-count").textContent).toBe("1");
    expect(screen.getByTestId("notification-count").textContent).toBe("1");
  });

  it("relays order_status_updated without touching the notification list", async () => {
    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    const socket = MockWebSocket.instances[0];

    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        event: "order_status_updated",
        data: {
          order_id: "order-1",
          old_status: "paid",
          new_status: "shipped",
          message: "Your order order-1 has been shipped.",
          timestamp: "2026-08-24T10:00:00Z",
        },
      });
    });

    expect(screen.getByTestId("notification-count").textContent).toBe("0");
    expect(notifyOrderStatusChangedMock).toHaveBeenCalledWith(
      expect.objectContaining({ order_id: "order-1", new_status: "shipped" })
    );
  });

  it("relays cart_updated to notifyCartChanged", async () => {
    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1));
    const socket = MockWebSocket.instances[0];

    act(() => {
      socket.emitOpen();
      socket.emitMessage({
        event: "cart_updated",
        data: { message: "Cart updated", total_items: 2, cart_total: "10.00" },
      });
    });

    expect(notifyCartChangedMock).toHaveBeenCalledTimes(1);
  });

  it("reconnects with 1s, then 2s, then 4s backoff after repeated drops", async () => {
    vi.useFakeTimers();

    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => MockWebSocket.instances[0].emitClose());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(999);
    });
    expect(MockWebSocket.instances).toHaveLength(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => MockWebSocket.instances[1].emitClose());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1999);
    });
    expect(MockWebSocket.instances).toHaveLength(2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(MockWebSocket.instances).toHaveLength(3);

    act(() => MockWebSocket.instances[2].emitClose());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3999);
    });
    expect(MockWebSocket.instances).toHaveLength(3);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(MockWebSocket.instances).toHaveLength(4);
  });

  it("resets the backoff counter after a successful connection", async () => {
    vi.useFakeTimers();

    render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    act(() => MockWebSocket.instances[0].emitClose());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(MockWebSocket.instances).toHaveLength(2);

    act(() => MockWebSocket.instances[1].emitOpen());
    act(() => MockWebSocket.instances[1].emitClose());

    await act(async () => {
      await vi.advanceTimersByTimeAsync(999);
    });
    expect(MockWebSocket.instances).toHaveLength(2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(MockWebSocket.instances).toHaveLength(3);
  });

  it("stops reconnecting once the component unmounts", async () => {
    vi.useFakeTimers();

    const { unmount } = render(
      <NotificationProvider>
        <Probe />
      </NotificationProvider>
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(MockWebSocket.instances).toHaveLength(1);

    act(() => MockWebSocket.instances[0].emitClose());
    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(MockWebSocket.instances).toHaveLength(1);
  });
});
