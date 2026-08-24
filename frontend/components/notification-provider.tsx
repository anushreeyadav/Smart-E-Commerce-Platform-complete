"use client";

import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useAuth } from "@/components/auth-provider";
import {
  buildNotificationSocketUrl,
  fetchNotifications,
  getBackendToken,
  markNotificationsAsRead,
  Notification,
  notifyCartChanged,
  notifyOrderStatusChanged,
  OrderStatusUpdatedPayload,
} from "@/lib/storefront";

type NotificationContextValue = {
  notifications: Notification[];
  unreadCount: number;
  markAllAsRead: () => Promise<void>;
  markAsRead: (notificationId: string) => Promise<void>;
};

const NotificationContext =
  createContext<NotificationContextValue | null>(null);

const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 16000, 30000];

export function NotificationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { isLoggedIn } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const reconnectAttemptRef = useRef(0);
  const manualCloseRef = useRef(false);
  const connectingRef = useRef(false);

  const refreshNotifications = async () => {
    if (!isLoggedIn) {
      setNotifications([]);
      return;
    }

    try {
      const data = await fetchNotifications();
      setNotifications(data);
    } catch {
      setNotifications([]);
    }
  };

  const markAllAsRead = async () => {
    const hadUnread = notifications.some(
      (notification) => !notification.read_status
    );

    if (!hadUnread) {
      return;
    }

    setNotifications((current) =>
      current.map((notification) => ({
        ...notification,
        read_status: true,
      }))
    );

    try {
      await markNotificationsAsRead([], true);
    } catch {}
  };

  const markAsRead = async (notificationId: string) => {
    const target = notifications.find(
      (notification) => notification.id === notificationId
    );

    if (!target || target.read_status) {
      return;
    }

    setNotifications((current) =>
      current.map((notification) =>
        notification.id === notificationId
          ? { ...notification, read_status: true }
          : notification
      )
    );

    try {
      await markNotificationsAsRead([notificationId], false);
    } catch {}
  };

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimeoutRef.current !== null) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    manualCloseRef.current = false;

    const scheduleReconnect = () => {
      if (manualCloseRef.current || !isLoggedIn) {
        return;
      }

      const attempt = reconnectAttemptRef.current;
      const delay =
        RECONNECT_DELAYS_MS[
          Math.min(attempt, RECONNECT_DELAYS_MS.length - 1)
        ];

      reconnectAttemptRef.current = attempt + 1;

      clearReconnectTimer();
      reconnectTimeoutRef.current = setTimeout(() => {
        void connect();
      }, delay);
    };

    const connect = async () => {
      if (!isLoggedIn) {
        return;
      }

      if (
        connectingRef.current ||
        (socketRef.current &&
          (socketRef.current.readyState === WebSocket.OPEN ||
            socketRef.current.readyState === WebSocket.CONNECTING))
      ) {
        return;
      }

      connectingRef.current = true;

      try {
        const token = await getBackendToken();

        if (!token || manualCloseRef.current || !isLoggedIn) {
          connectingRef.current = false;
          return;
        }

        const socket = new WebSocket(buildNotificationSocketUrl(token));
        socketRef.current = socket;

        socket.onopen = () => {
          connectingRef.current = false;
          reconnectAttemptRef.current = 0;
        };

        socket.onmessage = (event) => {
          let payload: { event: string; data: unknown };

          try {
            payload = JSON.parse(event.data);
          } catch {
            return;
          }

          if (payload.event === "notification_created") {
            const notification = payload.data as Notification;

            setNotifications((current) => [
              notification,
              ...current.filter(
                (existing) => existing.id !== notification.id
              ),
            ]);
          }

          if (payload.event === "order_status_updated") {
            notifyOrderStatusChanged(
              payload.data as OrderStatusUpdatedPayload
            );
          }

          if (payload.event === "cart_updated") {
            notifyCartChanged();
          }
        };

        socket.onerror = () => {};

        socket.onclose = () => {
          connectingRef.current = false;

          if (socketRef.current === socket) {
            socketRef.current = null;
          }

          scheduleReconnect();
        };
      } catch {
        connectingRef.current = false;
        scheduleReconnect();
      }
    };

    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshNotifications();

    if (isLoggedIn) {
      void connect();
    } else {
      manualCloseRef.current = true;
      clearReconnectTimer();
      socketRef.current?.close();
      socketRef.current = null;
    }

    return () => {
      manualCloseRef.current = true;
      clearReconnectTimer();
      socketRef.current?.close();
      socketRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoggedIn]);

  const unreadCount = notifications.filter(
    (notification) => !notification.read_status
  ).length;

  const value = useMemo<NotificationContextValue>(
    () => ({
      notifications,
      unreadCount,
      markAllAsRead,
      markAsRead,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [notifications, unreadCount]
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);

  if (!context) {
    throw new Error(
      "useNotifications must be used within a NotificationProvider"
    );
  }

  return context;
}
